use crate::{agent_error::ImlAgentError, cmd::cmd_output};
use librpm::Index;

pub async fn check_stratagem(_: ()) -> Result<bool, ImlAgentError> {
    librpm::config::read_file(None).unwrap();

    let mut matches = Index::Name.find("lipe");
    let package = matches.next();
    if package.is_some() {
        Ok(true)
    } else {
        Ok(false)
    }
}
