group "default" {
  targets = ["python-service-base", "systemd-base", "rust-base", "rust-service-base", "iml-gui"]
}


target "python-service-base" {
  dockerfile = "docker/python-service-base.dockerfile"
  context = "../"
  tags = ["imlteam/python-service-base:6.3.0"]
}

target "systemd-base" {
  dockerfile = "docker/systemd-base.dockerfile"
  context = "../"
  tags = ["imlteam/systemd-base:6.3.0"]
}

target "rust-base" {
  dockerfile = "docker/rust-base.dockerfile"
  context = "../"
  tags = ["rust-iml-base"]
}

target "rust-service-base" {
  dockerfile = "docker/rust-service-base.dockerfile"
  context = "../"
  tags = ["imlteam/rust-service-base:6.3.0"]
}

target "iml-gui" {
  dockerfile = "docker/iml-gui.dockerfile"
  context = "../"
  tags = ["rust-iml-gui"]
}
