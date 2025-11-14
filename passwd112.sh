SSH_OLD_CMD="sshpass -p $OLD_PWD ssh $IPMODE -q -o StrictHostKeyChecking=no mano@"

CHANGE_HA_USER_PASSWORD() {
  echo "Update HA user password"
 # $SSH_OLD_CMD$HA_IP_ADDR "echo -e \"$OLD_PWD\n$NEW_PWD\n$NEW_PWD\" | sudo -S passwd mano &>/dev/null"
   $SSH_OLD_CMD$HA_IP_ADDR "printf '%s\n%s\n' '$NEW_PWD' '$NEW_PWD' | sudo -S passwd mano &>/dev/null"
  if [ $? -eq 0 ]; then
    echo "Success to update HA user password!"
  else
    echo "Fail to update HA user password!"
    exit 1
  fi

  echo "Log out HA node sessions with user mano"
  sessions=$($SSH_CMD$HA_IP_ADDR "who" | awk '$1 == "mano" { print $2 }')
  for session in $sessions
  do
    echo $NEW_PWD | $SSH_CMD$HA_IP_ADDR "sudo -S pkill -9 -t $session &>/dev/null"
  done
}
