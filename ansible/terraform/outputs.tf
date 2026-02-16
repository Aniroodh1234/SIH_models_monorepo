output "abuse_ip" {
  value = aws_instance.abuse_model.public_ip
}

output "vision_ip" {
  value = aws_instance.vision_model.public_ip
}

output "voice_ip" {
  value = aws_instance.voice_model.public_ip
}
