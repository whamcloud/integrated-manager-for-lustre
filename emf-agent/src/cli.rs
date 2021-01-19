// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use console::{style, Term};
use emf_agent::action_plugins::{
    check_kernel, check_stonith, high_availability, kernel_module, lamigo, lpurge, lustre,
    ntp::{action_configure, is_ntp_configured},
    ostpool, package, postoffice,
    stratagem::{
        action_purge, action_warning,
        server::{
            generate_cooked_config, stream_fidlists, trigger_scan, Counter, StratagemCounters,
        },
    },
};
use emf_wire_types::{client, snapshot};
use liblustreapi as llapi;
use prettytable::{cell, row, Table};
use spinners::{Spinner, Spinners};
use std::{
    convert::TryInto,
    env,
    fs::File,
    io::{self, BufRead, BufReader},
    path::PathBuf,
    process::exit,
};
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum StratagemCommand {
    /// Kickoff a Stratagem scan
    #[structopt(name = "scan")]
    Scan {
        /// The full path of the device to scan
        #[structopt(short = "d", long = "device")]
        device_path: String,
        /// The report duration
        #[structopt(short = "r", long = "report", parse(try_from_str = parse_duration))]
        rd: Option<u64>,
        /// The purge duration
        #[structopt(short = "p", long = "purge", parse(try_from_str = parse_duration))]
        pd: Option<u64>,
    },
    /// Stream a fidlist
    #[structopt(name = "streamfidlist")]
    StreamFidList {
        /// Directory to stream up
        #[structopt(short = "d", long = "dir")]
        dir: PathBuf,
        /// Mailbox to stream fids to
        #[structopt(short = "m", long = "mailbox")]
        mailbox: String,
    },
}

#[derive(Debug, StructOpt)]
pub struct FsPool {
    #[structopt(name = "FILESYSTEM", parse(try_from_str = is_valid_fsname))]
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
        #[structopt(name = "FILESYSTEM", parse(try_from_str = is_valid_fsname))]
        filesystem: String,
    },
}

#[derive(Debug, StructOpt)]
pub enum PostOfficeCommand {
    #[structopt(name = "add")]
    Add {
        #[structopt(name = "MAILBOX")]
        mailbox: String,
    },
    #[structopt(name = "remove")]
    Remove {
        #[structopt(name = "MAILBOX")]
        mailbox: String,
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

#[derive(Debug, StructOpt)]
pub enum KernelModuleCommand {
    #[structopt(name = "loaded")]
    /// Is the module loaded?
    Loaded {
        #[structopt(name = "module")]
        module: String,
    },
    #[structopt(name = "version")]
    /// What is the version of the module?
    Version {
        #[structopt(name = "module")]
        module: String,
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
    if src.is_empty() {
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

    #[structopt(name = "FSNAME", parse(try_from_str = is_valid_fsname))]
    /// Lustre filesystem name, or mountpoint
    fsname: String,

    #[structopt(name = "FIDS")]
    /// List of FIDs to operate on
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

#[derive(Debug, StructOpt)]
pub enum NtpClientCommand {
    #[structopt(name = "configure")]
    /// Configure Ntp
    Configure {
        #[structopt(short = "s")]
        server: Option<String>,
    },

    #[structopt(name = "is_configured")]
    /// Is Ntp configured?
    IsConfigured,
}

#[derive(Debug, StructOpt)]
pub enum SnapshotCommand {
    /// Create a snapshot
    Create(snapshot::Create),
    /// Destroy the snapshot
    Destroy(snapshot::Destroy),
    /// Mount a snapshot
    Mount(snapshot::Mount),
    /// Unmount a snapshot
    Unmount(snapshot::Unmount),
    /// List snapshots.
    List(snapshot::List),
}

#[derive(Debug, StructOpt)]
pub enum MountCommand {
    /// Mount a client
    Mount(client::Mount),
    /// Unmount a client
    Unmount(client::Unmount),
}

#[derive(Debug, StructOpt)]
pub enum HighAvailability {
    #[structopt(name = "check")]
    Check,

    #[structopt(name = "list")]
    List,

    #[structopt(name = "start")]
    Start { resource: String },

    #[structopt(name = "stop")]
    Stop { resource: String },
}

#[derive(StructOpt, Debug)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
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

    #[structopt(name = "ha")]
    HA {
        #[structopt(subcommand)]
        command: HighAvailability,
    },

    #[structopt(name = "ntp")]
    NtpClient {
        #[structopt(subcommand)]
        command: NtpClientCommand,
    },
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

    #[structopt(name = "mount")]
    /// Mount lustre device
    Mount {
        #[structopt(subcommand)]
        command: MountCommand,
    },

    #[structopt(name = "kernel_module")]
    /// Get kernel module state and version
    KernelModule {
        #[structopt(subcommand)]
        command: KernelModuleCommand,
    },

    #[structopt(name = "lpurge")]
    /// Write `lpurge` configuration file
    LPurge {
        #[structopt(flatten)]
        c: lpurge::Config,
    },

    #[structopt(name = "lamigo")]
    /// Create `lamigo` systemd unit
    LAmigo {
        #[structopt(flatten)]
        c: lamigo::Config,
    },

    #[structopt(name = "postoffice")]
    /// Add or Remove PostOffice routes
    PostOffice {
        #[structopt(subcommand)]
        cmd: PostOfficeCommand,
    },

    #[structopt(name = "snapshot")]
    /// Snapshot operations
    Snapshot {
        #[structopt(subcommand)]
        command: SnapshotCommand,
    },
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

    t.add_row(row![name, x.count(), b.to_string()]);

    h.add_entry(name, x.count().try_into().unwrap());
}

fn exe_name() -> Option<String> {
    Some(
        std::env::current_exe()
            .ok()?
            .file_stem()?
            .to_str()?
            .to_string(),
    )
}

// FIXME: dedup with emf-manager-cli
fn selfname(suffix: Option<&str>) -> Option<String> {
    match env::var("CLI_NAME") {
        Ok(n) => suffix.map(|s| format!("{}-{}", n, s)).or(Some(n)),
        Err(_) => exe_name(),
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let name = selfname(Some("agent")).unwrap_or_else(|| "emf-agent".to_string());
    let matches = App::from_clap(&App::clap().bin_name(&name).name(&name).get_matches());

    dotenv::from_path("/etc/emf/emf-agent.conf").expect("Could not load cli env");

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
                let s = format!(
                    "{} {}...",
                    style("Scanning").cyan(),
                    style(&device_path).bold(),
                );

                let sp = Spinner::new(Spinners::Dots9, s);

                let data = generate_cooked_config(device_path, rd, pd);

                let result = trigger_scan(data).await;

                sp.stop();

                if let Err(e) = Term::stdout().clear_line() {
                    tracing::debug!("Could not clear current line {}", e);
                };

                match result {
                    Ok((results_dir, output, _)) => {
                        println!(
                            "{}. Results located in {}",
                            style("✔ Scan finished").green(),
                            results_dir
                        );

                        for x in output.group_counters {
                            println!(
                                "\n\n\n{} {}\n",
                                style("Group:").cyan().bold(),
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
            StratagemCommand::StreamFidList { dir, mailbox } => {
                let arg = vec![(dir, mailbox)];

                if let Err(e) = stream_fidlists(arg).await {
                    tracing::error!("Failed to stream fids: {:?}", e);
                }
            }
        },
        App::HA { command } => match command {
            HighAvailability::Check => match high_availability::check_ha(()).await {
                Ok((cs, pm, pc)) => {
                    let mut table = Table::new();
                    table.add_row(row!["Name", "Config", "Service"]);
                    table.add_row(row!["corosync", cs.config, cs.service]);
                    table.add_row(row!["pacemaker", pm.config, pm.service]);
                    table.add_row(row!["pcsd", pc.config, pc.service]);
                    table.printstd();
                }
                Err(e) => {
                    eprintln!("{:?}", e);
                    exit(exitcode::SOFTWARE);
                }
            },
            HighAvailability::List => match high_availability::get_ha_resource_list(()).await {
                Ok(v) => {
                    for e in v {
                        println!("{}", serde_json::to_string(&e).unwrap())
                    }
                }
                Err(e) => {
                    eprintln!("Failed to list resources: {:?}", e);
                    exit(exitcode::SOFTWARE);
                }
            },
            HighAvailability::Start { resource } => {
                if let Err(e) = high_availability::start_resource(resource).await {
                    eprintln!("{:?}", e);
                    exit(exitcode::SOFTWARE);
                }
            }
            HighAvailability::Stop { resource } => {
                if let Err(e) = high_availability::stop_resource(resource).await {
                    eprintln!("{:?}", e);
                    exit(exitcode::SOFTWARE);
                }
            }
        },
        App::NtpClient { command } => match command {
            NtpClientCommand::Configure { server } => {
                fn get_ntp_message(server: &Option<String>) -> String {
                    if let Some(server) = &server {
                        format!("Ntp configured with server {}", server)
                    } else {
                        "Ntp configuration reset".to_string()
                    }
                }

                let msg = get_ntp_message(&server);
                match action_configure::update_and_write_new_config(server).await {
                    Ok(_) => {
                        println!("{}", msg);
                        println!("Restarting ntpd daemon.");
                        match emf_systemd::restart_unit("ntpd".into()).await {
                            Ok(_) => {
                                println!("ntpd service restarted successfully.");
                            }
                            Err(e) => {
                                eprintln!("{:?}", e);
                            }
                        }
                    }
                    Err(e) => eprintln!("{:?}", e),
                }
            }

            NtpClientCommand::IsConfigured => {
                match is_ntp_configured::is_ntp_configured(()).await {
                    Ok(configured) => {
                        if configured {
                            println!("Ntp is configured on this server.");
                        } else {
                            println!("Ntp is not configured on this server.");
                        }
                    }
                    Err(e) => eprintln!("{:?}", e),
                }
            }
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
            Err(e) => eprintln!("{:?}", e),
        },
        App::Package { command } => {
            if let Err(e) = match command {
                PackageCommand::Installed { package_name } => package::installed(package_name)
                    .await
                    .map(|r| println!("{}", if r { "Installed" } else { "Not Installed" })),
                PackageCommand::Version { package_name } => {
                    package::version(package_name).await.map(|r| match r {
                        Some(v) => println!("{}", v),
                        None => {
                            eprintln!("no version");
                            exit(exitcode::DATAERR)
                        }
                    })
                }
            } {
                eprintln!("{:?}", e);
                exit(exitcode::SOFTWARE);
            }
        }
        App::GetKernel { modules } => match check_kernel::get_kernel(modules).await {
            Ok(s) => println!("{}", s),
            Err(e) => {
                eprintln!("{:?}", e);
                exit(exitcode::SOFTWARE);
            }
        },
        App::Mount { command } => {
            if let Err(e) = match command {
                MountCommand::Mount(m) => lustre::client::mount(m).await,
                MountCommand::Unmount(u) => lustre::client::unmount(u).await,
            } {
                eprintln!("{}", e);
                exit(exitcode::SOFTWARE);
            }
        }

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
                eprintln!("{:?}", e);
                exit(exitcode::SOFTWARE);
            }
        }
        App::PostOffice { cmd } => {
            if let Err(e) = match cmd {
                PostOfficeCommand::Add { mailbox } => postoffice::route_add(mailbox).await,
                PostOfficeCommand::Remove { mailbox } => postoffice::route_remove(mailbox).await,
            } {
                eprintln!("{:?}", e);
                exit(exitcode::SOFTWARE);
            }
        }
        App::KernelModule { command } => {
            if let Err(e) = match command {
                KernelModuleCommand::Loaded { module } => kernel_module::loaded(module)
                    .await
                    .map(|r| println!("{}", if r { "Loaded" } else { "Not Loaded" })),
                KernelModuleCommand::Version { module } => kernel_module::version(module)
                    .await
                    .map(|r| println!("{}", r)),
            } {
                eprintln!("{}", e);
                exit(exitcode::SOFTWARE);
            }
        }
        App::LPurge { c } => {
            if let Err(e) = lpurge::create_lpurge_conf(c).await {
                eprintln!("{}", e);
                exit(exitcode::SOFTWARE);
            }
        }
        App::LAmigo { c } => {
            if let Err(e) = lamigo::create_lamigo_conf(c).await {
                eprintln!("{}", e);
                exit(exitcode::SOFTWARE);
            }
        }
        App::Snapshot { command } => {
            if let Err(e) = match command {
                SnapshotCommand::Create(c) => lustre::snapshot::create(c).await,
                SnapshotCommand::Destroy(d) => lustre::snapshot::destroy(d).await,
                SnapshotCommand::Mount(m) => lustre::snapshot::mount(m).await,
                SnapshotCommand::Unmount(u) => lustre::snapshot::unmount(u).await,
                SnapshotCommand::List(l) => lustre::snapshot::list(l)
                    .await
                    .map(|snaps| println!("{:?}", snaps)),
            } {
                eprintln!("{}", e);
                exit(exitcode::SOFTWARE);
            }
        }
    };

    Ok(())
}
