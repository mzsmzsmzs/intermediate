#!/usr/bin/env bash
# vnf_backup_restore_sim.sh
# Simulate backup and restore of a VNF cluster in KubeVirt using a custom CRD that manages VNF backups.
# Output is ONLY logs. No real commands are executed. Compatible with macOS default bash (no associative arrays).

set -u

timestamp() { date +"%F %T"; }
log() { local msg="$1"; local TS; TS=$(timestamp); printf '[%s] %s
' "$TS" "$msg"; }

# Progress bar: label, duration_seconds
progress_bar() {
  local label="$1"; local duration="$2"; local start now elapsed pct i j
  start=$(date +%s)
  printf "%-40s [" "$label"
  while true; do
    now=$(date +%s)
    elapsed=$((now - start))
    if [ "$elapsed" -ge "$duration" ]; then pct=100; i=40; else pct=$((elapsed * 100 / duration)); i=$((pct * 40 / 100)); fi
    for ((j=0; j<i; j++)); do printf "#"; done
    for ((j=i; j<40; j++)); do printf " "; done
    printf "] %3d%%
" "$pct"
    if [ "$pct" -ge 100 ]; then break; fi
    sleep 0.2
    printf "%-40s [" "$label"
  done
  printf "
"
}

# Simulated VM backup and package restore
simulate_vm_backup() {
  local vm="$1"; local size_mb="$2"
  log "START backup of VM: $vm | PV size: ${size_mb}MB | target: external-storage://backups/$vm.tgz"
  local duration=$(( (size_mb / 50) + 2 ))
  progress_bar "Backing up $vm" "$duration"
  log "COMPLETE backup of VM: $vm | stored at external-storage://backups/$vm.tgz"
}
simulate_pkg_restore() { local pkg="$1"; log "Restoring package: $pkg"; sleep 1; log "Restore complete: $pkg"; }

# ---------- Simulated cluster state ----------
RTRV_OUTPUT=(
  "vnf-node-01 ACTIVE"
  "vnf-node-02 ACTIVE"
  "vnf-node-03 STANDBY"
  "vnf-node-04 STANDBY"
  "vnf-node-05 ACTIVE"
)

NODE_VMS_LIST=(
  "vnf-node-01:vnf-a vnf-b"
  "vnf-node-02:vnf-c"
  "vnf-node-03:vnf-d"
  "vnf-node-04:vnf-e vnf-f"
  "vnf-node-05:vnf-g"
)
VM_SIZE_LIST=(
  "vnf-a:1200"
  "vnf-b:800"
  "vnf-c:600"
  "vnf-d:400"
  "vnf-e:200"
  "vnf-f:300"
  "vnf-g:900"
)

get_vms_for_node() { local node="$1"; local entry; for entry in "${NODE_VMS_LIST[@]}"; do case "$entry" in "$node:"*) printf '%s' "${entry#*:}"; return;; esac; done; printf '
'; }
get_vm_size() { local vm="$1"; local entry; for entry in "${VM_SIZE_LIST[@]}"; do case "$entry" in "$vm:"*) printf '%s' "${entry#*:}"; return;; esac; done; printf '300'; }

# ---------- CRD simulation helpers ----------
# Simulate checking CRD existence
simulate_crd_check() {
  log "Checking for VnfBackup CRD: vnfbackups.mydomain/v1"
  sleep 0.6
  log "CRD vnfbackups.mydomain/v1: present"
}

# Simulate creating a VnfBackup custom resource for a node or VM
simulate_create_vnfbackup_cr() {
  local name="$1"; local target="$2"
  log "Creating VnfBackup CR: name=$name target=$target"
  sleep 0.5
  log "VnfBackup/$name created. status=Pending"
}

# Simulate monitoring the CR status transitions
simulate_monitor_cr_status() {
  local name="$1"
  log "Monitoring VnfBackup/$name status"
  sleep 0.6
  log "VnfBackup/$name status=InProgress"
  progress_bar "CRD:${name} backup progress" 3
  sleep 0.3
  log "VnfBackup/$name status=Completed"
}

# ---------- Phases with CRD integration ----------
pre_checks() {
  log "PHASE: Pre-checks"
  log "Verifying backup packages: BKUP.PKG, CRTE-FW.PKG"
  sleep 0.5
  log "BKUP.PKG: available"
  log "CRTE-FW.PKG: available"
  sleep 0.4

  log "Running RTRV-NODE-STS to gather VNF node status"
  for line in "${RTRV_OUTPUT[@]}"; do log "RTRV-NODE-STS > $line"; done

  ACTIVE_NODES=()
  STANDBY_NODES=()
  local node state
  for line in "${RTRV_OUTPUT[@]}"; do
    node=$(printf '%s' "$line" | awk '{print $1}')
    state=$(printf '%s' "$line" | awk '{print $2}')
    if [ "$state" = "ACTIVE" ]; then ACTIVE_NODES+=("$node"); else STANDBY_NODES+=("$node"); fi
  done

  log "Grouped nodes"
  printf "
%-15s | %-10s
" "NODE" "ROLE"
  printf "%-15s-+-%-10s
" "---------------" "----------"
  for line in "${RTRV_OUTPUT[@]}"; do
    node=$(printf '%s' "$line" | awk '{print $1}')
    state=$(printf '%s' "$line" | awk '{print $2}')
    printf "%-15s | %-10s
" "$node" "$state"
  done
  printf "
"

  simulate_crd_check
}

backup_standby_vms_via_crd() {
  log "PHASE: Backup standby VMs via VnfBackup CRD"
  local node vms vm size crname
  for node in "${STANDBY_NODES[@]}"; do
    log "Preparing VnfBackup CR for standby node: $node"
    vms=$(get_vms_for_node "$node")
    crname="backup-${node}-$(date +%s)"
    simulate_create_vnfbackup_cr "$crname" "node:$node"
    simulate_monitor_cr_status "$crname"
    # After CR reports Completed, simulate creating per-VM backup artifacts
    for vm in $vms; do
      [ -z "$vm" ] && continue
      size=$(get_vm_size "$vm")
      simulate_vm_backup "$vm" "$size"
      sleep 0.3
    done
  done
}

perform_ffo_and_backup_active_via_crd() {
  log "PHASE: FFO / Switchover and backup of previously active VMs via CRD"
  log "Initiating fast failover (FFO). Switchover expected in 1 second."
  sleep 1
  log "Switchover complete. Standby nodes promoted to active."

  # swap arrays
  local tmp; tmp=("${ACTIVE_NODES[@]}"); ACTIVE_NODES=("${STANDBY_NODES[@]}"); STANDBY_NODES=("${tmp[@]}")
  log "New ACTIVE nodes: ${ACTIVE_NODES[*]}"

  # create CRs for previous-active nodes now in STANDBY_NODES
  local node vms vm crname
  for node in "${STANDBY_NODES[@]}"; do
    log "Creating VnfBackup CR for previous-active node: $node"
    crname="backup-prevactive-${node}-$(date +%s)"
    simulate_create_vnfbackup_cr "$crname" "node:$node"
    simulate_monitor_cr_status "$crname"
    vms=$(get_vms_for_node "$node")
    for vm in $vms; do
      [ -z "$vm" ] && continue
      size=$(get_vm_size "$vm")
      simulate_vm_backup "$vm" "$size"
      sleep 0.25
    done
  done
}

post_checks_and_restore_flow() {
  log "PHASE: Post-checks"
  log "Verifying compute host health and KubeVirt platform services"
  sleep 0.8
  if [ $((RANDOM % 4)) -eq 0 ]; then
    local down_host="${ACTIVE_NODES[0]}"
    log "ALERT: Detected compute host down: $down_host"
    log "Operator action: Re-installing platform on $down_host"
    sleep 2
    log "Platform re-installation complete on $down_host"
    log "Restoring VMs on $down_host from backups"
    local vms vm
    vms=$(get_vms_for_node "$down_host")
    for vm in $vms; do
      [ -z "$vm" ] && continue
      log "Restoring VM $vm to $down_host from external-storage://backups/$vm.tgz"
      progress_bar "Restoring $vm" 3
      log "VM restore complete: $vm"
    done
  else
    log "All compute hosts healthy"
  fi

  log "Restoring VNF backup data via CRD-driven restore"
  local crname="restore-system-$(date +%s)"
  simulate_create_vnfbackup_cr "$crname" "system:restore"
  simulate_monitor_cr_status "$crname"
  simulate_pkg_restore "BKUP.PKG"
  simulate_pkg_restore "CRTE-FW.PKG"
  sleep 0.6

  log "Running post-sync to update IDs across cloud ecosystems"
  progress_bar "Syncing IDs across cloud DBs" 4
  log "Post-sync complete. BKUP-PKG DB and ports updated."
  log "CRTE-FW-PKG mappings validated and synchronized."
}

final_summary() {
  log "PHASE: Summary"
  printf "
+------------------------------+
"
  printf "| Backup and Restore Summary   |
"
  printf "+------------------------------+
"
  printf "Total nodes evaluated : %s
" "${#RTRV_OUTPUT[@]}"
  printf "Active nodes now       : %s
" "${ACTIVE_NODES[*]}"
  printf "Standby nodes now      : %s
" "${STANDBY_NODES[*]}"
  printf "Backups stored at      : external-storage://backups/
"
  printf "Key packages           : BKUP.PKG, CRTE-FW.PKG
"
  printf "Checks performed       : RTRV-NODE-STS, VnfBackup CRD create/monitor, PV backup, package restore, ID sync
"
  printf "+------------------------------+
"
  log "complete"
}

main() {
  echo
  log "Starting VNF Cluster backup and restore  using VnfBackup CRD"
  echo
  pre_checks
  echo
  backup_standby_vms_via_crd
  echo
  perform_ffo_and_backup_active_via_crd
  echo
  post_checks_and_restore_flow
  echo
  final_summary
}

main
