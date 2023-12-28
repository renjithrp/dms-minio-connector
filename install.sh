#!/bin/bash
INSTALL_DIR='/usr/local/minio-connector'
INSTALL_USER='minio'
sudo apt install git poppler-utils python3 python3-pip -y
sudo pip3 install -r requirements.txt
sudo mkdir -p $INSTALL_DIR && /bin/cp -r connector $INSTALL_DIR
sudo useradd -m -d $INSTALL_DIR -s /bin/bash $INSTALL_USER
sudo chown -R $INSTALL_USER:$INSTALL_USER $INSTALL_USER
sudo /bin/cp minio-connector.service /etc/systemd/system/minio-connector.service
sudo sed -i "s|\(WorkingDirectory=\).*|\1$INSTALL_DIR|g" /etc/systemd/system/minio-connector.service
sudo sed -i "s|\(Environment=.*PYTHONPATH=\).*|\1$INSTALL_DIR/connector/src\"|g" /etc/systemd/system/minio-connector.service
sudo sed -i "s|\(ExecStart=\).*|\1$INSTALL_DIR/connector/run.sh|g" /etc/systemd/system/minio-connector.service
sudo sed -i "s/\(User=\).*/\1$INSTALL_USER/g" /etc/systemd/system/minio-connector.service
sudo sed -i "s/\(Group=\).*/\1$INSTALL_USER/g" /etc/systemd/system/minio-connector.service
sudo systemctl daemon-reload
sudo systemctl start minio-connector
sudo systemctl enable minio-connector
sudo systemctl status minio-connector