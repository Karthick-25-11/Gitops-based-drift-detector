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