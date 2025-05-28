resource "aws_ssm_parameter" "model_temperature" {
    name = "extract-model-temperature"
    type = "String"
    value = "0"
    tags = {
        Name = var.tag_name
    }
}