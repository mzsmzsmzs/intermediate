comm -12 <(awk -F'-' '{print $1}' rpversion_patch.txt | sort) <(awk -F'-' '{print $1}' 9version_patch.txt | sort) > common_names_with_versions.txt


#!/bin/bash

# Step 1: Extract package names from `rpversion_patch.txt` and `9version_patch.txt`
awk '{match($0, /^[^-]+/); print substr($0, RSTART, RLENGTH)}' rpversion_patch.txt | sort > rp_names.txt
awk '{match($0, /^[^-]+/); print substr($0, RSTART, RLENGTH)}' 9version_patch.txt | sort > 9_names.txt

# Step 2: Find common package names
comm -12 rp_names.txt 9_names.txt > common_names.txt

# Step 3: Extract full entries for common package names along with versions
awk 'NR==FNR {names[$1]; next} {name=$0; match(name, /^[^-]+/); pkg_name=substr(name, RSTART, RLENGTH); if (pkg_name in names) print pkg_name, "rpversion:", name}' common_names.txt rpversion_patch.txt > rp_matches.txt

awk 'NR==FNR {names[$1]; next} {name=$0; match(name, /^[^-]+/); pkg_name=substr(name, RSTART, RLENGTH); if (pkg_name in names) print pkg_name, "9version:", name}' common_names.txt 9version_patch.txt > 9_matches.txt

# Step 4: Merge results for common package names
join -j 1 <(sort rp_matches.txt) <(sort 9_matches.txt) > common_packages_with_versions.txt

# Step 5: Cleanup intermediate files
rm rp_names.txt 9_names.txt common_names.txt rp_matches.txt 9_matches.txt

echo "Output saved in common_packages_with_versions.txt"


#!/bin/bash

# Step 1: Extract package names (until the first numeric) from `rpversion_patch.txt` and `9version_patch.txt`
awk '{match($0, /^[^-]*[^0-9-]/); print substr($0, RSTART, RLENGTH)}' rpversion_patch.txt | sort > rp_names.txt
awk '{match($0, /^[^-]*[^0-9-]/); print substr($0, RSTART, RLENGTH)}' 9version_patch.txt | sort > 9_names.txt

# Step 2: Find common package names
comm -12 rp_names.txt 9_names.txt > common_names.txt

# Step 3: Extract full entries (with versions) for common package names
awk 'NR==FNR {names[$1]; next} {
    match($0, /^[^-]*[^0-9-]/);
    pkg_name = substr($0, RSTART, RLENGTH);
    if (pkg_name in names) print pkg_name, "rpversion:", $0
}' common_names.txt rpversion_patch.txt > rp_matches.txt

awk 'NR==FNR {names[$1]; next} {
    match($0, /^[^-]*[^0-9-]/);
    pkg_name = substr($0, RSTART, RLENGTH);
    if (pkg_name in names) print pkg_name, "9version:", $0
}' common_names.txt 9version_patch.txt > 9_matches.txt

# Step 4: Merge results for common package names
join -j 1 <(sort rp_matches.txt) <(sort 9_matches.txt) > common_packages_with_versions.txt

# Step 5: Cleanup intermediate files
rm rp_names.txt 9_names.txt common_names.txt rp_matches.txt 9_matches.txt

echo "Output saved in common_packages_with_versions.txt"


#!/bin/bash

# Step 1: Extract package names (until the first numeric) from `rpversion_patch.txt` and `9version_patch.txt`
awk '{match($0, /^[^-]+(-[^-]+)*[^0-9-]/); print substr($0, RSTART, RLENGTH)}' rpversion_patch.txt | sort > rp_names.txt
awk '{match($0, /^[^-]+(-[^-]+)*[^0-9-]/); print substr($0, RSTART, RLENGTH)}' 9version_patch.txt | sort > 9_names.txt

# Step 2: Find common package names
comm -12 rp_names.txt 9_names.txt > common_names.txt

# Step 3: Extract full entries (with versions) for common package names
awk 'NR==FNR {names[$1]; next} {
    match($0, /^[^-]+(-[^-]+)*[^0-9-]/);
    pkg_name = substr($0, RSTART, RLENGTH);
    if (pkg_name in names) print pkg_name, "rpversion:", $0
}' common_names.txt rpversion_patch.txt > rp_matches.txt

awk 'NR==FNR {names[$1]; next} {
    match($0, /^[^-]+(-[^-]+)*[^0-9-]/);
    pkg_name = substr($0, RSTART, RLENGTH);
    if (pkg_name in names) print pkg_name, "9version:", $0
}' common_names.txt 9version_patch.txt > 9_matches.txt

# Step 4: Merge results for common package names
join -j 1 <(sort rp_matches.txt) <(sort 9_matches.txt) > common_packages_with_versions.txt

# Step 5: Cleanup intermediate files
rm rp_names.txt 9_names.txt common_names.txt rp_matches.txt 9_matches.txt

echo "Output saved in common_packages_with_versions.txt"

awk 'NR==FNR {
    # Read common names into an array
    names[$1]; 
    next
} {
    # Extract package name until the first numeric character
    match($0, /^[^0-9]*/);
    pkg_name = substr($0, RSTART, RLENGTH);
    # Print full line if the package name is in the common list
    if (pkg_name in names) print pkg_name, "rpversion:", $0
}' common_names.txt rpversion_patch.txt > rp_matches.txt
awk 'NR==FNR {
    # Read common names into an array
    names[$1]; 
    next
} {
    # Extract package name until the first numeric character
    match($0, /^[^0-9]*/);
    pkg_name = substr($0, RSTART, RLENGTH);
    # Print full line if the package name is in the common list
    if (pkg_name in names) print pkg_name, "9version:", $0
}' common_names.txt 9version_patch.txt > 9_matches.txt





