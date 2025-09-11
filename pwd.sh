CHANGE_USER_PASSWORD() {
  echo "Update user password"
  echo "old $OLD_PWD new: $NEW_PWD\n"
  echo -e "$OLD_PWD\n$NEW_PWD\n$NEW_PWD" | sudo -S passwd mano
  if [ $? -eq 0 ]; then
    echo "Success to update user password!"
  else
    echo "Fail to update user password!"
    exit 1
  fi
