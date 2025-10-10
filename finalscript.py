#!/usr/bin/env python3
"""
vnf_backup_crd_controller.py

VNF Cluster Backup and Restore Controller using VnfBackup CRD.
All operations are log-only. Includes progress bars and realistic workflow.
"""

import sys, time, random, datetime, yaml
from tqdm import tqdm
from typing import List, Dict

# ------------------ Utility functions ------------------

def now_ts(): 
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def log(msg: str):
    print(f"[{now_ts()}] {msg}")

def progress_bar(label: str, duration: int):
    for _ in tqdm(range(duration), desc=label, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s", ncols=80):
        time.sleep(1)

# ------------------ Cluster & VM Data ------------------

RTRV_OUTPUT = [
    ("vnf-node-01", "ACTIVE"),
    ("vnf-node-02", "ACTIVE"),
    ("vnf-node-03", "STANDBY"),
    ("vnf-node-04", "STANDBY"),
    ("vnf-node-05", "ACTIVE"),
]

NODE_VMS_LIST = {
    "vnf-node-01": ["vnf-a", "vnf-b"],
    "vnf-node-02": ["vnf-c"],
    "vnf-node-03": ["vnf-d"],
    "vnf-node-04": ["vnf-e", "vnf-f"],
    "vnf-node-05": ["vnf-g"]
}

VM_SIZE_LIST = {
    "vnf-a": 1200,
    "vnf-b": 800,
    "vnf-c": 600,
    "vnf-d": 400,
    "vnf-e": 200,
    "vnf-f": 300,
    "vnf-g": 900
}

# ------------------ Global Node Lists ------------------
ACTIVE_NODES: List[str] = []
STANDBY_NODES: List[str] = []

# ------------------ CRD Helpers ------------------

def create_vnfbackup_cr(name: str, target: str):
    log(f"Creating VnfBackup CR: name={name} target={target}")
    time.sleep(0.5)
    log(f"VnfBackup/{name} created. status=Pending")

def monitor_cr_status(name: str):
    log(f"Monitoring VnfBackup/{name} status")
    time.sleep(0.5)
    log(f"VnfBackup/{name} status=InProgress")
    progress_bar(f"CRD:{name} backup progress", 3)
    time.sleep(0.3)
    log(f"VnfBackup/{name} status=Completed")

def backup_vm(vm: str, size_mb: int):
    log(f"START backup of VM: {vm} | PV size: {size_mb}MB | target: external-storage://backups/{vm}.tgz")
    duration = (size_mb // 50) + 2
    progress_bar(f"Backing up {vm}", duration)
    log(f"COMPLETE backup of VM: {vm} | stored at external-storage://backups/{vm}.tgz")

def backup_db(db_name: str):
    log(f"Starting database backup: {db_name}")
    progress_bar(f"DB Backup {db_name}", 2)
    log(f"Database backup complete: {db_name}")

def backup_volume(pvc: str):
    log(f"Backing up volume: {pvc} using CSI snapshot")
    progress_bar(f"Volume Backup {pvc}", 2)
    log(f"Volume backup complete: {pvc}")

def backup_file(pod: str, path_includes: List[str], path_excludes: List[str]):
    log(f"Backing up files from pod: {pod}")
    for p in path_includes:
        progress_bar(f"File Backup {pod}:{p}", 1)
    log(f"Excluding paths: {', '.join(path_excludes)}")
    log(f"File backup complete for pod: {pod}")

def restore_pkg(pkg: str):
    log(f"Restoring package: {pkg}")
    time.sleep(1)
    log(f"Restore complete: {pkg}")

# ------------------ Controller Phases ------------------

def pre_checks():
    global ACTIVE_NODES, STANDBY_NODES
    log("PHASE: Pre-checks")
    log("Verifying backup packages: BKUP.PKG, CRTE-FW.PKG")
    time.sleep(0.5)
    log("BKUP.PKG: available")
    log("CRTE-FW.PKG: available")
    time.sleep(0.3)
    
    log("Running RTRV-NODE-STS to gather VNF node status")
    for node, state in RTRV_OUTPUT:
        log(f"RTRV-NODE-STS > {node} {state}")
        if state == "ACTIVE": ACTIVE_NODES.append(node)
        else: STANDBY_NODES.append(node)
    
    log("Grouped nodes:")
    print(f"\n{'NODE':<15} | {'ROLE':<10}")
    print(f"{'-'*15}-+-{'-'*10}")
    for node, state in RTRV_OUTPUT:
        print(f"{node:<15} | {state:<10}")
    print("")
    
    log("Checking for VnfBackup CRD presence")
    time.sleep(0.5)
    log("CRD vnfbackups.mydomain/v1: present\n")

def backup_nodes(nodes: List[str], cr_prefix: str):
    for node in nodes:
        crname = f"{cr_prefix}-{node}-{int(time.time())}"
        create_vnfbackup_cr(crname, f"node:{node}")
        monitor_cr_status(crname)
        for vm in NODE_VMS_LIST.get(node, []):
            backup_vm(vm, VM_SIZE_LIST.get(vm, 300))

def backup_crd_components(crd: Dict):
    components = crd.get("spec", {}).get("components", [])
    for comp in components:
        typ = comp.get("type")
        if typ == "VirtualMachine":
            vm_name = comp["vmComponent"]["vmName"]
            backup_vm(vm_name, 500)  # Use 500MB default if not specified
        elif typ == "Database":
            dbs = comp["dbComponent"]["taskParams"]["databases"]
            for db in dbs:
                backup_db(db)
        elif typ == "Volume":
            pvc = comp["volumeComponent"]["pvcName"]
            backup_volume(pvc)
        elif typ == "File":
            pod = comp["fileComponent"]["podRef"]
            includes = comp["fileComponent"]["pathIncludes"]
            excludes = comp["fileComponent"]["pathExcludes"]
            backup_file(pod, includes, excludes)

def switchover():
    global ACTIVE_NODES, STANDBY_NODES
    log("PHASE: Fast Failover / Switchover")
    log("Initiating fast failover (FFO). Standby nodes promoted to active.")
    time.sleep(1)
    ACTIVE_NODES, STANDBY_NODES = STANDBY_NODES, ACTIVE_NODES
    log(f"New ACTIVE nodes: {ACTIVE_NODES}")
    log(f"New STANDBY nodes: {STANDBY_NODES}")

def post_checks_and_restore():
    log("PHASE: Post-checks and restore")
    # Randomly simulate a host down
    down_host = None
    if random.randint(0,3) == 0:
        down_host = ACTIVE_NODES[0]
        log(f"ALERT: Detected compute host down: {down_host}")
        log(f"Operator action: Re-installing platform on {down_host}")
        time.sleep(2)
        log(f"Platform re-installation complete on {down_host}")
        for vm in NODE_VMS_LIST.get(down_host, []):
            log(f"Restoring VM {vm} to {down_host} from external-storage://backups/{vm}.tgz")
            progress_bar(f"Restoring {vm}", 3)
            log(f"VM restore complete: {vm}")
    else:
        log("All compute hosts healthy")
    
    # CRD-driven restore
    crname = f"restore-system-{int(time.time())}"
    create_vnfbackup_cr(crname, "system:restore")
    monitor_cr_status(crname)
    restore_pkg("BKUP.PKG")
    restore_pkg("CRTE-FW.PKG")
    
    # Post-sync
    progress_bar("Syncing IDs across cloud DBs", 4)
    log("Post-sync complete. BKUP-PKG DB and ports updated.")
    log("CRTE-FW-PKG mappings validated and synchronized.")

def final_summary():
    log("PHASE: Summary")
    print("\n+------------------------------+")
    print("| Backup and Restore Summary   |")
    print("+------------------------------+")
    print(f"Total nodes evaluated : {len(RTRV_OUTPUT)}")
    print(f"Active nodes now      : {ACTIVE_NODES}")
    print(f"Standby nodes now     : {STANDBY_NODES}")
    print(f"Backups stored at     : external-storage://backups/")
    print(f"Key packages          : BKUP.PKG, CRTE-FW.PKG")
    print(f"Checks performed      : RTRV-NODE-STS, VnfBackup CRD create/monitor, PV backup, package restore, ID sync")
    print("+------------------------------+\n")
    log("Backup and restore operation completed.")

# ------------------ Main flow ------------------

def main():
    log("Starting VNF Cluster backup and restore using VnfBackup CRD\n")
    pre_checks()
    # Backup standby nodes first
    backup_nodes(STANDBY_NODES, "backup-standby")
    # Switchover / FFO
    switchover()
    # Backup previous active nodes (now standby)
    backup_nodes(STANDBY_NODES, "backup-prevactive")
    # Backup CRD components (VM/DB/Volume/File) for full policy (optional)
    # You can load from real CRD YAML if needed
    # backup_crd_components(crd) 
    post_checks_and_restore()
    final_summary()

if __name__ == "__main__":
    main()
