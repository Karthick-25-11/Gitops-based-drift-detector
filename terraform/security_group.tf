# 1. Define the Security Group
resource "aws_security_group" "demo_sg_v2" {
  name        = "demo-sg-v2"
  description = "Security group for GitOps Drift MVP"

  # Your Python logic currently checks these ingress ports
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
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

# 2. Define the EC2 Instance
resource "aws_instance" "app_server" {
  ami           = "ami-091138d0f0d41ff90" 
  
  # Your Python logic will now monitor this attribute for drift
  instance_type = "t3.small"

  vpc_security_group_ids = [aws_security_group.demo_sg_v2.id]

  tags = {
    Name = "GitOps-Intelligence-Demo"
    ManagedBy = "Terraform"
  }
}