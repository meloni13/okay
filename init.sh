sudo yum update -y
sudo yum install -y python3-pip
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

cp backend.service /etc/systemd/system/backend.service
cp backend.py /home/ec2-user/backend.py

cp -r CSE546-SPRING-2025-model /home/ec2-user/