use llapi;
use std::env;

fn cwd() -> String {
    String::from(
        env::current_dir()
            .expect("Failed to get CWD")
            .to_str()
            .expect("Failed to show CWD"),
    )
}

fn main() {
    let device = cwd();

    for fid in env::args() {
        println!("Looking at {}", &fid);

        match llapi::fid2path(&device, &fid) {
            Some(path) => println!("{} -> {}", fid, path),
            None => (),
        }
    }
}
