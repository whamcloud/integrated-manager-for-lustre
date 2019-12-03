// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_agent::action_plugins::stratagem::{
    action_purge, action_warning,
    server::{generate_cooked_config, trigger_scan, Counter, StratagemCounters},
};
use iml_agent::action_plugins::{
    check_ha, check_kernel, check_stonith, ostpool, package,
};
use liblustreapi as llapi;
use prettytable::{cell, row, Table};
use spinners::{Spinner, Spinners};
use std::{
    convert::TryInto,
    fs::File,
    io::{self, BufRead, BufReader},
    process::exit,
};
use structopt::StructOpt;
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

#[derive(Debug, StructOpt)]
pub enum StratagemCommand {
    /// Kickoff a Stratagem scan
    #[structopt(name = "scan")]
    Scan {
        /// The full path of the device to scan
        #[structopt(short = "d", long = "device")]
        device_path: String,
        /// The report duration
        #[structopt(short = "r", long = "report", parse(try_from_str = "parse_duration"))]
        rd: Option<u64>,
        /// The purge duration
        #[structopt(short = "p", long = "purge", parse(try_from_str = "parse_duration"))]
        pd: Option<u64>,
    },
}

#[derive(Debug, StructOpt)]
pub struct FsPool {
    #[structopt(name = "FILESYSTEM", parse(try_from_str = "is_valid_fsname"))]
    filesystem: String,

    #[structopt(name = "POOL")]
    pool: String,
}

#[derive(Debug, StructOpt)]
pub struct FsPoolOst {
    #[structopt(flatten)]
    fspool: FsPool,

    #[structopt(name = "OST")]
    ost: String,
}

#[derive(Debug, StructOpt)]
pub enum PoolCommand {
    #[structopt(name = "create")]
    Create {
        #[structopt(flatten)]
        cmd: FsPool,
    },
    #[structopt(name = "destroy")]
    Destroy {
        #[structopt(flatten)]
        cmd: FsPool,
    },
    #[structopt(name = "add")]
    Add {
        #[structopt(flatten)]
        cmd: FsPoolOst,
    },
    #[structopt(name = "remove")]
    Remove {
        #[structopt(flatten)]
        cmd: FsPoolOst,
    },
    #[structopt(name = "list")]
    List {
        #[structopt(name = "FILESYSTEM", parse(try_from_str = "is_valid_fsname"))]
        filesystem: String,
    },
}

#[derive(Debug, StructOpt)]
pub enum PackageCommand {
    #[structopt(name = "installed")]
    Installed {
        #[structopt(name = "package_name")]
        package_name: String,
    },
    #[structopt(name = "version")]
    Version {
        #[structopt(name = "package_name")]
        package_name: String,
    },
}

fn invalid_input_err(msg: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidInput, msg)
}

fn parse_duration(src: &str) -> Result<u64, io::Error> {
    if src.len() < 2 {
        return Err(invalid_input_err(
            "Invalid value specified. Must be a valid integer.",
        ));
    }

    let mut val = String::from(src);
    let unit = val.pop();

    let val = val
        .parse::<u64>()
        .map_err(|_| invalid_input_err(&format!("Could not parse {} to u64", val)))?;

    match unit {
        Some('h') => Ok(val * 3_600_000),
        Some('d') => Ok(val * 86_400_000),
        Some('m') => Ok(val * 60_000),
        Some('s') => Ok(val * 1_000),
        Some('1'..='9') => Err(invalid_input_err("No unit specified.")),
        _ => Err(invalid_input_err(
            "Invalid unit. Valid units include 'h' and 'd'.",
        )),
    }
}

/// Use with structop parse to validate lustre filesystem name
fn is_valid_fsname(src: &str) -> Result<String, io::Error> {
    // c.f. lustre-release/lustre/utils/mkfs_lustre.c::parse_opts for
    // 'L' (fsname) option
    if src.len() < 1 {
        return Err(invalid_input_err("FSName too short (min length 1)"));
    }
    if src.len() > llapi::MAXFSNAME {
        return Err(invalid_input_err(&format!(
            "FSName too long (max length {})",
            llapi::MAXFSNAME
        )));
    }
    for c in src.chars() {
        if !c.is_ascii_alphanumeric() && c != '-' && c != '_' {
            return Err(invalid_input_err(&format!(
                "Invalid character in fsname ({})",
                c
            )));
        }
    }
    Ok(src.to_string())
}

#[derive(Debug, StructOpt)]
pub struct FidInput {
    #[structopt(short = "i")]
    /// File to read from, "-" for stdin, or unspecified for on cli
    input: Option<String>,

    #[structopt(name = "FSNAME", parse(try_from_str = "is_valid_fsname"))]
    /// Lustre filesystem name, or mountpoint
    fsname: String,

    #[structopt(name = "FIDS")]
    /// List of FIDs to purge
    fidlist: Vec<String>,
}

#[derive(Debug, StructOpt)]
pub enum StratagemClientCommand {
    #[structopt(name = "warning")]
    /// Run warning action
    Warning {
        #[structopt(short = "o")]
        /// File to write to, or "-" or unspecified for stdout
        output: Option<String>,

        #[structopt(flatten)]
        fidopts: FidInput,
    },

    #[structopt(name = "purge")]
    /// Run purge action
    Purge {
        #[structopt(flatten)]
        fidopts: FidInput,
    },
}

#[derive(StructOpt, Debug)]
#[structopt(name = "iml-agent")]
/// The Integrated Manager for Lustre Agent CLI
pub enum App {
    #[structopt(name = "stratagem")]
    /// Work with Stratagem server
    StratagemServer {
        #[structopt(subcommand)]
        command: StratagemCommand,
    },

    #[structopt(name = "stratagem_client")]
    /// Work with Stratagem client
    StratagemClient {
        #[structopt(subcommand)]
        command: StratagemClientCommand,
    },

    #[structopt(name = "pool")]
    Pool {
        #[structopt(subcommand)]
        command: PoolCommand,
    },

    #[structopt(name = "check_ha")]
    CheckHA,

    #[structopt(name = "check_stonith")]
    CheckStonith,

    #[structopt(name = "package")]
    Package {
        #[structopt(subcommand)]
        command: PackageCommand,
    },

    #[structopt(name = "get_kernel")]
    /// Get latest kernel which supports listed modules
    GetKernel { modules: Vec<String> },
}

fn input_to_iter(input: Option<String>, fidlist: Vec<String>) -> Box<dyn Iterator<Item = String>> {
    match input {
        None => {
            if fidlist.is_empty() {
                Box::new(
                    BufReader::new(io::stdin())
                        .lines()
                        .map(|x| x.expect("Failed to readline from stdin")),
                )
            } else {
                Box::new(fidlist.into_iter())
            }
        }
        Some(name) => {
            let buf: Box<dyn BufRead> = match name.as_ref() {
                "-" => Box::new(BufReader::new(io::stdin())),
                _ => {
                    let f = match File::open(&name) {
                        Ok(x) => x,
                        Err(e) => {
                            tracing::error!("Failed to open {}: {}", &name, e);
                            exit(exitcode::CANTCREAT);
                        }
                    };
                    Box::new(BufReader::new(f))
                }
            };
            Box::new(
                buf.lines()
                    .map(|x| x.expect("Failed to readline from file")),
            )
        }
    }
}

fn humanize(s: &str) -> String {
    s.replace('_', " ")
}

/// Takes a `Vec` of `StratagemCounters` and
/// prints a histogram and table for each one.
///
/// If a `StratagemClassifyCounter` is encountered, this
/// fn will recurse and print the nested counter before the parent.
fn print_counters(xs: Vec<StratagemCounters>) {
    tracing::info!("Looking at: {:?}", xs);

    let mut table = Table::new();
    table.add_row(row!["Name", "Count", "Used"]);

    let mut h = v_hist::init();
    h.max_width = 50;

    if xs.is_empty() {
        return;
    }

    for x in xs {
        add_counter_entry(&x, &mut table, &mut h);

        if let StratagemCounters::StratagemClassifyCounter(x) = x {
            print_counters(
                x.classify
                    .counters
                    .into_iter()
                    .map(StratagemCounters::StratagemCounter)
                    .collect(),
            );
        }
    }

    h.draw();

    println!("\n\n");

    table.printstd();
}

fn add_counter_entry(x: impl Counter, t: &mut Table, h: &mut v_hist::Histogram) {
    let name = humanize(&x.name());

    let b = byte_unit::Byte::from_bytes(x.size().into()).get_appropriate_unit(true);

    t.add_row(row![name.clone(), x.count(), b.to_string()]);

    h.add_entry(name, x.count().try_into().unwrap());
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let matches = App::from_args();

    match matches {
        App::StratagemClient { command: cmd } => match cmd {
            StratagemClientCommand::Purge { fidopts: opt } => {
                let device = opt.fsname;

                if action_purge::purge_files(&device, opt.fidlist).is_err() {
                    exit(exitcode::OSERR);
                }
            }
            StratagemClientCommand::Warning {
                output: out,
                fidopts: opt,
            } => {
                let device = opt.fsname;
                let output: Box<dyn io::Write> = match out {
                    Some(file) => Box::new(File::create(file).expect("Failed to create file")),
                    None => Box::new(io::stdout()),
                };
                let input = input_to_iter(opt.input, opt.fidlist);

                if action_warning::write_records(&device, input, output).is_err() {
                    exit(exitcode::IOERR);
                }
            }
        },
        App::StratagemServer { command } => match command {
            StratagemCommand::Scan {
                device_path,
                rd,
                pd,
            } => {
                let cyan = termion::color::Fg(termion::color::Cyan);
                let green = termion::color::Fg(termion::color::Green);
                let reset = termion::color::Fg(termion::color::Reset);

                let s = format!(
                    "{}Scanning{} {}{}{}...",
                    cyan,
                    reset,
                    termion::style::Bold,
                    device_path,
                    reset,
                );
                let s_len = s.len();

                let sp = Spinner::new(Spinners::Dots9, s);

                let data = generate_cooked_config(device_path, rd, pd);

                let result = trigger_scan(data).await;

                sp.stop();
                println!("{}", termion::clear::CurrentLine);
                print!("{}", termion::cursor::Left(s_len as u16));

                match result {
                    Ok((results_dir, output, _)) => {
                        println!(
                            "{}✔ Scan finished{}. Results located in {}",
                            green, reset, results_dir
                        );

                        for x in output.group_counters {
                            println!(
                                "\n\n\n{}{}Group:{} {}\n",
                                cyan,
                                termion::style::Bold,
                                reset,
                                humanize(&x.name)
                            );

                            print_counters(x.counters);
                        }
                    }
                    Err(e) => {
                        eprintln!("{}", e);

                        exit(exitcode::SOFTWARE);
                    }
                };
            }
        },
        App::CheckHA => match check_ha::check_ha(()).await {
            Ok(v) => {
                for e in v {
                    println!("{}", serde_json::to_string(&e).unwrap())
                }
            }
            Err(e) => println!("{:?}", e),
        },
        App::CheckStonith => match check_stonith::check_stonith(()).await {
            Ok(cs) => {
                println!(
                    "{}: {}",
                    if cs.state {
                        "Configured"
                    } else {
                        "Unconfigured"
                    },
                    cs.info
                );
            }
            Err(e) => println!("{:?}", e),
        },
        App::Package { command } => match command {
            PackageCommand::Installed { package_name } => {
                match package::installed(package_name).await {
                    Ok(cs) => {
                        println!("{}", if cs { "Installed" } else { "Not Installed" });
                    }
                    Err(e) => println!("{:?}", e),
                }
            }
            PackageCommand::Version { package_name } => {
                match package::version(package_name).await {
                    Ok(v) => {
                        println!("{:?}", v);
                    }
                    Err(e) => println!("{:?}", e),
                }
            }
        },
        App::GetKernel { modules } => match check_kernel::get_kernel(modules).await {
            Ok(s) => println!("{}", s),
            Err(e) => println!("{:?}", e),
        },
        App::Pool { command } => {
            if let Err(e) = match command {
                PoolCommand::Create { cmd } => ostpool::pool_create(cmd.filesystem, cmd.pool).await,
                PoolCommand::Destroy { cmd } => {
                    ostpool::pool_destroy(cmd.filesystem, cmd.pool).await
                }
                PoolCommand::Add { cmd } => {
                    ostpool::pool_add(cmd.fspool.filesystem, cmd.fspool.pool, cmd.ost).await
                }
                PoolCommand::Remove { cmd } => {
                    ostpool::pool_remove(cmd.fspool.filesystem, cmd.fspool.pool, cmd.ost).await
                }
                PoolCommand::List { filesystem } => ostpool::pools(filesystem).await.map(|list| {
                    for pool in list {
                        println!("{}", pool)
                    }
                }),
            } {
                println!("{:?}", e);
                exit(exitcode::SOFTWARE);
            }
        }
    };

    Ok(())
}
