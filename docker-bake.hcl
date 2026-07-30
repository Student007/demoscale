variable "REGISTRY_USER" {
  default = "danbu"
}

variable "IMAGE_REPOSITORY" {
  default = "demoscale"
}

variable "IMAGE_TAG" {
  default = "1.2.9"
}

group "default" {
  targets = ["dashboard", "producer", "worker", "bundle-task"]
}

target "_common" {
  context = "."
  platforms = ["linux/amd64", "linux/arm64"]
}

target "dashboard" {
  inherits = ["_common"]
  dockerfile = "dashboard/Dockerfile"
  tags = ["${REGISTRY_USER}/${IMAGE_REPOSITORY}:demoscale-dashboard-${IMAGE_TAG}"]
}

target "producer" {
  inherits = ["_common"]
  dockerfile = "producer/Dockerfile"
  tags = ["${REGISTRY_USER}/${IMAGE_REPOSITORY}:demoscale-producer-${IMAGE_TAG}"]
}

target "worker" {
  inherits = ["_common"]
  dockerfile = "worker/Dockerfile"
  tags = ["${REGISTRY_USER}/${IMAGE_REPOSITORY}:demoscale-worker-${IMAGE_TAG}"]
}

target "bundle-task" {
  inherits = ["_common"]
  dockerfile = "bundle/Dockerfile"
  tags = ["${REGISTRY_USER}/${IMAGE_REPOSITORY}:demoscale-bundle-task-${IMAGE_TAG}"]
}
