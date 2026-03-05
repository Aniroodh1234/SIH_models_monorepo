provider "aws" {
  region = "ap-south-1"
}

# Key Pair (assuming user has one, or generating a new one is safer? User didn't specify.
# I will use a data source to look for 'default' or create one if specific name provided.
# For now, let's assume a key exists or create one from a local public key.)
# To be safe and automated, let's create a key pair using the local id_rsa.pub if it exists.

resource "aws_key_pair" "deployer" {
  key_name   = "sih-deployer-key"
  public_key = file("${path.module}/../.key/id_rsa.pub")
}

# Security Group
resource "aws_security_group" "sih_sg" {
  name        = "sih_models_sg"
  description = "Allow SSH And HTTP"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP Nginx"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Opening app ports for debugging/direct access if needed, though Nginx proxies to them locally.
  ingress {
    description = "Abuse Model"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Voice Model"
    from_port   = 8001
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Vision Model"
    from_port   = 8002
    to_port     = 8002
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# AMI Data Source for Ubuntu 22.04
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}

# 1. Abuse Model - t2.small (8GB is default for t2, but user asked specifically.
# t2.small has 1 vCPU, 2GB RAM. User request: "abuse model t2.small (8 gb)".
# GP2 volume size is configured in block_device_mappings.
resource "aws_instance" "abuse_model" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.small"
  key_name      = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.sih_sg.id]

  root_block_device {
    volume_size = 8
    volume_type = "gp2"
  }

  tags = {
    Name = "Abuse-Model"
    Role = "abuse"
  }
}

# 2. Vision Model - t2.medium 20gb
resource "aws_instance" "vision_model" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.medium"
  key_name      = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.sih_sg.id]

  root_block_device {
    volume_size = 20
    volume_type = "gp2"
  }

  tags = {
    Name = "Vision-Model"
    Role = "vision"
  }
}

# 3. Voice Model - t2.large 50gb
resource "aws_instance" "voice_model" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.large"
  key_name      = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.sih_sg.id]

  root_block_device {
    volume_size = 50
    volume_type = "gp2"
  }

  tags = {
    Name = "Voice-Model"
    Role = "voice"
  }
}
