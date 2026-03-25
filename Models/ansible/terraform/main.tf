provider "aws" {
  region = "ap-south-1"
}

# Key Pair — uses the shared SSH key from .key/
resource "aws_key_pair" "cat_deployer" {
  key_name_prefix = "cat-deployer-key-"
  public_key      = file("${path.module}/../.key/id_rsa.pub")
}

# Security Group
resource "aws_security_group" "cat_sg" {
  name_prefix = "cat_model_sg-"
  description = "Auto-categorization AI: SSH + HTTP/S + FastAPI"

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

  # FastAPI (8000)
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # All outbound (pip, git, API calls)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "cat-model-sg"
  }
}

# Ubuntu 22.04 AMI
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

# EC2 Instance — Auto-categorization AI
resource "aws_instance" "categorization_model" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.medium"
  key_name      = aws_key_pair.cat_deployer.key_name
  vpc_security_group_ids = [aws_security_group.cat_sg.id]

  root_block_device {
    volume_size = 25
    volume_type = "gp3"
  }

  tags = {
    Name = "Auto-Categorization-AI"
    Role = "categorization"
  }
}
