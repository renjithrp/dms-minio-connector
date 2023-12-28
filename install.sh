#!/bin/bash
INSTALL_DIR='/usr/local/minio-connector'
INSTALL_USER='minio'
SERVICE_FILE='/etc/systemd/system/minio-connector.service'

remove_service() {
    sudo systemctl stop minio-connector
    sudo systemctl disable minio-connector
    sudo rm -f "$SERVICE_FILE"
    sudo userdel -r "$INSTALL_USER"
    sudo groupdel "$INSTALL_USER"
    exit 0
}

if [[ $1 == 'remove' ]]; then
    remove_service
fi

install_packages() {
    sudo apt update
    sudo apt install -y git poppler-utils python3 python3-pip
}

install_python_packages() {
    sudo pip3 install -r requirements.txt
}

copy_files() {
    sudo mkdir -p "$INSTALL_DIR" && /bin/cp -r connector/* "$INSTALL_DIR/"
}

create_user() {
    sudo useradd -m -d "$INSTALL_DIR" -s /bin/bash "$INSTALL_USER"
    sudo chown -R "$INSTALL_USER":"$INSTALL_USER" "$INSTALL_DIR"
}

setup_service() {
    sudo /bin/cp minio-connector.service "$SERVICE_FILE"
    sudo sed -i "s|WorkingDirectory=.*|WorkingDirectory=$INSTALL_DIR/|g" "$SERVICE_FILE"
    sudo sed -i "s|Environment=.*PYTHONPATH=.*|Environment=PYTHONPATH=$INSTALL_DIR/src|g" "$SERVICE_FILE"
    sudo sed -i "s|ExecStart=.*|ExecStart=$INSTALL_DIR/run.sh|g" "$SERVICE_FILE"
    sudo sed -i "s/User=.*/User=$INSTALL_USER/g" "$SERVICE_FILE"
    sudo sed -i "s/Group=.*/Group=$INSTALL_USER/g" "$SERVICE_FILE"
}

main() {
    install_packages
    install_python_packages
    copy_files
    create_user
    setup_service

    sudo systemctl daemon-reload
    sudo systemctl start minio-connector
    sudo systemctl enable minio-connector
    sudo systemctl status minio-connector
}

main