provider "aws" {
  region = "ap-south-1"
}

# Key Pair (assuming user has one, or generating a new one is safer? User didn't specify.
# I will use a data source to look for 'default' or create one if specific name provided.
# For now, let's assume a key exists or create one from a local public key.)
# To be safe and automated, let's create a key pair using the local id_rsa.pub if it exists.

resource "aws_key_pair" "deployer" {
  key_name_prefix = "sih-deployer-key-"
  public_key      = file("${path.module}/../.key/id_rsa.pub")
}

# Security Group — created and managed by Terraform
resource "aws_security_group" "sih_sg" {
  name_prefix = "sih_models_sg-"
  description = "SIH Models: SSH + HTTP/S + FastAPI ports"

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP (Nginx)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # FastAPI — Abuse (8000), Voice (8001), Vision (8002)
  ingress {
    from_port   = 8000
    to_port     = 8002
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound (for pip installs, git clone, API calls)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "sih-models-sg"
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


# 1. Vision Model (also runs Abuse model) - t2.medium, 25 GB
resource "aws_instance" "vision_model" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.medium"
  key_name      = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.sih_sg.id]

  root_block_device {
    volume_size = 25
    volume_type = "gp2"
  }

  tags = {
    Name = "Vision-Abuse-Combined"
    Role = "vision"
  }
}

# 2. Voice Model - t2.large 50gb
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
