comm -12 <(awk -F'-' '{print $1}' rpversion_patch.txt | sort) <(awk -F'-' '{print $1}' 9version_patch.txt | sort) > common_names_with_versions.txt
