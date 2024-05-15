sudo apt update
sudo apt install openssh-server
sudo ufw allow ssh
sudo apt-get install samba
sudo smbpasswd -a hjpark
sudo sed -i '$a[homes]' /etc/samba/smb.conf
sudo sed -i '$acomment = hjpark ims pc' /etc/samba/smb.conf
sudo sed -i '$a	path = /home/hjpark' /etc/samba/smb.conf
sudo sed -i '$awriteable = yes' /etc/samba/smb.conf
sudo sed -i '$abrowseable = yes' /etc/samba/smb.conf
sudo sed -i '$a	valid users = hjpark, root' /etc/samba/smb.conf
sudo service smbd restart
