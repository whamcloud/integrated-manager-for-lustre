group "default" {
  targets = ["python-service-base", "systemd-base", "rust-base", "rust-service-base", "emf-gui"]
}


target "python-service-base" {
  dockerfile = "docker/python-service-base.dockerfile"
  context = "../"
  tags = ["emfteam/python-service-base:6.3.0"]
}

target "systemd-base" {
  dockerfile = "docker/systemd-base.dockerfile"
  context = "../"
  tags = ["emfteam/systemd-base:6.3.0"]
}

target "rust-base" {
  dockerfile = "docker/rust-base.dockerfile"
  context = "../"
  tags = ["rust-emf-base"]
}

target "rust-service-base" {
  dockerfile = "docker/rust-service-base.dockerfile"
  context = "../"
  tags = ["emfteam/rust-service-base:6.3.0"]
}

target "emf-gui" {
  dockerfile = "docker/emf-gui.dockerfile"
  context = "../"
  tags = ["rust-emf-gui"]
}
