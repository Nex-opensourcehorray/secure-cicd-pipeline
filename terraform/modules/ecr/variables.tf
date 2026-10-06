variable "repository_name" {
  description = "Name of the private ECR repository."
  type        = string

  validation {
    condition     = length(trimspace(var.repository_name)) >= 2
    error_message = "repository_name must contain at least two characters."
  }
}

variable "max_tagged_images" {
  description = "Maximum number of recent tagged images to retain."
  type        = number
  default     = 20

  validation {
    condition     = var.max_tagged_images >= 10
    error_message = "max_tagged_images must retain at least 10 tagged images."
  }
}

variable "untagged_image_retention_days" {
  description = "Days to retain untagged images before expiration."
  type        = number
  default     = 14

  validation {
    condition     = var.untagged_image_retention_days >= 7
    error_message = "untagged_image_retention_days must be at least 7 days."
  }
}

variable "tags" {
  description = "Tags applied to the ECR repository."
  type        = map(string)
  default     = {}
}
