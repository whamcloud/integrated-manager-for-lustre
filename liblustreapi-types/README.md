*RE-BUILDING*

To build rebuild this either touch wrapper.h or remove src/bindings.rs
and rerun cargo build.

**EL7**

A note about building this bindgen (0.57) on el7, as this version of bindgen needs clang > 3.9:

As root:
``` sh
yum install -y centos-release-scl
yum install -y llvm-toolset-7
```

As local user
``` sh
cd liblustreapi-types/
rm src/bindings.rs
scl enable llvm-toolset-7 'cargo build'
```
