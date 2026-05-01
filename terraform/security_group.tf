resource "aws_security_group" "web-sg"{
    name        = "demo-sg"
    description = "allow  http only"
    ingress{
        description = "HTTP"
        from_port   = 80
        to_port     = 80
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }
}