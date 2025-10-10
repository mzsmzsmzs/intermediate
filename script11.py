#!/usr/bin/env python3
"""
vnf_backup_sim.py

Simulated VNF Backup Creator + Controller (prints logs only).

Features
- Load a VNFBackupConfiguration CRD from a YAML file or use an embedded CRD string.
- Determine VIMs (from CRD if present, or via --vims CLI argument, or fallback defaults).
- For each VIM, generate a simulated VNFBackup custom resource YAML (printed) and "apply" it.
- Simulate controller behavior: update a status condition named "backup-vm1" for all CRs and print logs.
- Print a summary ASCII table at the end.

Usage examples
- python3 vnf_backup_sim.py --crd-file my-crd.yaml
- python3 vnf_backup_sim.py --vims vim-a,vim-b
- python3 vnf_backup_sim.py --crd-file my-crd.yaml --controller
- python3 vnf_backup_sim.py            # uses embedded CRD and two default VIMs

Notes
- This is a simulator. It only prints logs and YAML text. No network or kubectl operations are performed.
- If PyYAML is available it will be used to parse the CRD. If not present a lightweight parser tries to extract a few keys.
"""

import sys
import argparse
import datetime
import json
import textwrap
from typing import List, Dict, Any, Optional

# --------- Embedded CRD (the one you supplied) ----------
EMBEDDED_CRD = """
apiVersion: telco.vnf.io/v1alpha1
kind: VNFBackupConfiguration
metadata:
  name: vnf-core-backup-policy
  namespace: telco-vnf-a
spec:
  # 1. Target and Storage Definition
  targetVNFRef:
    name: vnf-core-instance-01
    kind: VirtualNetworkFunction
    apiGroup: telco.vnf.io
  storageRef: "swift-vnf-backend-storage"
  # 2. Scheduling, Mode, and Retention Policy
  backupMode: Incremental
  schedule: "0 3 * * *"
  retentionPolicy:
    ttl: "720h0m0s"
    maxFulls: 7
    maxIncrementals: 30
  components:
    - type: VirtualMachine
      vmComponent:
        vmName: vnf-core-processor-vm-0
        consistencyMode: GuestAgent
        volumeSelection:
          - root-disk
          - configuration-disk
    - type: Database
      dbComponent:
        dbType: MariaDB
        appBindingRef: mariadb-vnf-appbinding
        addonName: mariadb-addon
        taskParams:
          databases:
            - core-telemetry
            - cdr-data
    - type: Volume
      volumeComponent:
        pvcName: general-storage-pvc
        useCSI: true
    - type: File
      fileComponent:
        podRef: vnf-config-manager-pod-0
        volumeMountName: 'config-volume'
        pathIncludes:
          - /etc/vnf/configs/
          - /var/log/startup-scripts/
        pathExcludes:
          - /etc/vnf/configs/tmp/logs
"""

# --------- Utility functions ----------
def now_ts() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def log(msg: str):
    print(f"[{now_ts()}] {msg}")

def ascii_table(rows: List[List[str]], headers: List[str]) -> str:
    # simple fixed-width ascii table
    cols = len(headers)
    col_widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            col_widths[i] = max(col_widths[i], len(cell))
    sep = "+".join("-" * (w + 2) for w in col_widths)
    sep = "+" + sep + "+"
    def fmt_row(r):
        return "| " + " | ".join(r[i].ljust(col_widths[i]) for i in range(cols)) + " |"
    lines = [sep, fmt_row(headers), sep]
    for r in rows:
        lines.append(fmt_row(r))
    lines.append(sep)
    return "\n".join(lines)

# --------- Lightweight YAML extraction if PyYAML not present ----------
def safe_load_yaml(yaml_text: str) -> dict:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(yaml_text) or {}
    except Exception:
        # Minimalist extraction: find top-level keys we care about
        d: Dict[str, Any] = {}
        lines = [ln.rstrip() for ln in yaml_text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        cur_path: List[str] = []
        for ln in lines:
            if ":" in ln:
                indent = len(ln) - len(ln.lstrip())
                key, val = ln.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                # crude hierarchy: indent by 2 spaces per level
                level = indent // 2
                # adjust path
                if level < len(cur_path):
                    cur_path = cur_path[:level]
                if val == "":
                    # mapping start
                    cur_path = cur_path[:level] + [key]
                    # create nested dicts
                    node = d
                    for p in cur_path:
                        if p not in node or not isinstance(node[p], dict):
                            node[p] = {}
                        node = node[p]
                else:
                    node = d
                    for p in cur_path:
                        node = node.setdefault(p, {})
                    node[key] = val
        return d

# --------- Simulator core ----------
class VNFBackupSimulator:
    def __init__(self, crd_text: str, vims: Optional[List[str]] = None, controller_mode: bool = False, simulate_steps: bool = True):
        self.raw_crd_text = crd_text
        self.crd = safe_load_yaml(crd_text)
        self.controller_mode = controller_mode
        self.simulate_steps = simulate_steps
        self.vims = vims or self._discover_vims() or ["vim-default-1","vim-default-2"]
        self.created_backups: List[Dict[str, Any]] = []

    def _discover_vims(self) -> List[str]:
        # try to find spec.vims or metadata.vims in CRD; fallback to empty
        keys = []
        try:
            spec = self.crd.get("spec", {})
            if isinstance(spec, dict) and "vims" in spec:
                v = spec.get("vims")
                if isinstance(v, str):
                    return [x.strip() for x in v.split(",") if x.strip()]
                if isinstance(v, list):
                    return v
        except Exception:
            pass
        return []

    def create_backup_cr_for_vim(self, vim: str) -> Dict[str, Any]:
        meta = self.crd.get("metadata", {})
        spec = self.crd.get("spec", {})
        target = spec.get("targetVNFRef", {})
        target_name = target.get("name") or meta.get("name") or "vnf-target"
        backup_name = f"vnfbackup-{vim}-{target_name}".lower().replace("_","-")
        namespace = meta.get("namespace","default")
        backup_cr = {
            "apiVersion": "telco.vnf.io/v1alpha1",
            "kind": "VNFBackup",
            "metadata": {
                "name": backup_name,
                "namespace": namespace,
                "labels": {
                    "originBackupPolicy": meta.get("name","vnf-core-backup-policy"),
                    "vim": vim
                }
            },
            "spec": {
                "policyRef": meta.get("name","vnf-core-backup-policy"),
                "targetVNFRef": target,
                "storageRef": spec.get("storageRef"),
                "backupMode": spec.get("backupMode","OneTime"),
                "components": spec.get("components", [])
            },
            "status": {
                "conditions": []
            }
        }
        return backup_cr

    def simulate_kubectl_apply(self, cr: Dict[str, Any]):
        yaml_text = json.dumps(cr, indent=2)
        log(f"Simulating: kubectl apply -f -  # resource: {cr['kind']}/{cr['metadata']['name']}")
        print("--- YAML START ---")
        print(yaml_text)
        print("--- YAML END ---")
        log(f"Applied simulated resource {cr['kind']}/{cr['metadata']['name']} in namespace {cr['metadata']['namespace']}")

    def run_backup_steps(self, cr: Dict[str, Any]):
        # Simulate the steps you provided for backup package / firmware etc.
        steps = [
            ("BKUP-PKG", "Take backup of existing package (TYPE = ALL (SW+DB))"),
            ("CRTE-FW-PKG", "Take backup of current firmware (fallback)"),
            ("DUMP-FW", "Dump firmware of the corresponding release version"),
            # Steps sequence
            ("RTRV-PKG-INF", "Retrieve package info"),
            ("DUMP-PKG", "Dump package file (simulate TAR read)"),
            ("ACT-DB-EVOL", "Activate DB evolution changes"),
            ("COPY-PKG", "Copy package to staging"),
            ("INIT-NEW-PKG", "Initialize new package"),
            ("RTRV-PKG-VER", "Retrieve new package version"),
        ]
        log(f"Starting simulated backup workflow for {cr['metadata']['name']}")
        for step_id, desc in steps:
            log(f"[{cr['metadata']['name']}] Step {step_id} - {desc} ...")
            # print a small fake progress bar using dots
            for i in range(3):
                print(".", end="", flush=True)
            print("")  # newline
        log(f"Completed simulated backup workflow for {cr['metadata']['name']}")

    def controller_update_backup_vm1(self):
        # Simulate controller updating condition 'backup-vm1' to True with timestamp
        for cr in self.created_backups:
            cond = {
                "type": "backup-vm1",
                "status": "True",
                "lastUpdateTime": now_ts(),
                "reason": "SimulatedBackupComplete",
                "message": f"Simulated backup for {cr['metadata']['name']} completed successfully"
            }
            cr_status = cr.setdefault("status", {})
            conds = cr_status.setdefault("conditions", [])
            conds.append(cond)
            log(f"Controller: updated status.backup-vm1 for {cr['metadata']['name']} -> True")

    def summarize(self):
        rows = []
        for cr in self.created_backups:
            name = cr['metadata']['name']
            vim = cr['metadata']['labels'].get('vim', '')
            # find backup-vm1 cond
            conds = cr.get("status", {}).get("conditions", [])
            vm1 = next((c for c in conds if c.get("type")=="backup-vm1"), None)
            status = vm1.get("status") if vm1 else "Pending"
            rows.append([vim, name, status])
        log("Summary of simulated backup instances:")
        print(ascii_table(rows, ["VIM", "BackupCR", "backup-vm1"]))

    def run(self):
        log("Starting VNF Backup Simulator")
        for vim in self.vims:
            log(f"Creating simulated backup instance for VIM '{vim}'")
            cr = self.create_backup_cr_for_vim(vim)
            self.simulate_kubectl_apply(cr)
            self.created_backups.append(cr)
            if self.simulate_steps:
                self.run_backup_steps(cr)
        if self.controller_mode:
            log("Running simulated controller updates")
            self.controller_update_backup_vm1()
        self.summarize()
        log("Simulator run complete")


# --------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser(
        description="Simulated VNF Backup creator + controller (prints logs only)."
    )
    p.add_argument("--crd-file", help="Path to VNFBackupConfiguration CRD YAML. If omitted uses embedded sample.")
    p.add_argument("--vims", help="Comma-separated list of VIM names to simulate. Overrides CRD vims if present.")
    p.add_argument("--no-steps", dest="steps", action="store_false", help="Do not simulate backup workflow steps.")
    p.add_argument("--controller", action="store_true", help="Simulate controller updates (status backup-vm1 updates).")
    return p.parse_args()

def main():
    args = parse_args()
    if args.crd_file:
        try:
            with open(args.crd_file, "r") as fh:
                crd_text = fh.read()
        except Exception as e:
            log(f"Error reading CRD file '{args.crd_file}': {e}")
            sys.exit(2)
    else:
        crd_text = EMBEDDED_CRD

    vims = None
    if args.vims:
        vims = [x.strip() for x in args.vims.split(",") if x.strip()]

    sim = VNFBackupSimulator(crd_text=crd_text, vims=vims, controller_mode=args.controller, simulate_steps=args.steps)
    sim.run()

if __name__ == "__main__":
    main()
