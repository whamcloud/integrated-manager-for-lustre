// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[cfg(feature = "xml")]
use elementtree::Element;

use std::{collections::BTreeMap, convert::TryFrom, fmt};

const INFINITY: i32 = 1_000_000;
const NEG_INFINITY: i32 = -1_000_000;

// helper function for printing optional arguments for crm
// ARG
fn arg_or_none<T>(arg: &str, value: &Option<T>) -> String
where
    T: fmt::Display,
{
    match value {
        None => "".to_string(),
        Some(x) => format!(" {}={}", arg, x),
    }
}

// helper function for printing optional arguments for crm
// ARG
fn op_or_none<T>(name: &str, value: &Option<T>) -> String
where
    T: ToCrmsh,
{
    match value {
        None => "".to_string(),
        Some(x) => format!(" op {} {}", name, x.to_crmsh()),
    }
}

fn something(s: &str) -> Option<&str> {
    if s.is_empty() {
        None
    } else {
        Some(s)
    }
}

/// id-spec to crmsh
fn idspec(value: &str) -> String {
    arg_or_none("$id", &something(value))
}

fn subid(parentid: &str, tag: &str, index: usize) -> String {
    if index == 0 {
        format!("{}-{}", parentid, tag)
    } else {
        format!("{}-{}-{}", parentid, tag, index - 1)
    }
}

fn qvalue(value: &str) -> String {
    if value.contains(&['/', '='][..]) {
        format!(r#""{}""#, value)
    } else {
        value.to_string()
    }
}

// helper function for printing nvlist with a "type" (e.g. meta or params)
fn nvlist_or_none(header: &str, nvlist: &[Nvpair], parentid: &str, tag: &str) -> String {
    if nvlist.is_empty() {
        "".to_string()
    } else {
        nvlist
            .iter()
            .enumerate()
            .map(|(index, nv)| {
                format!(
                    " {}{}",
                    &header,
                    nv.to_crmsh_wo_id(&subid(parentid, tag, index))
                )
            })
            .collect::<Vec<String>>()
            .join("")
    }
}

#[cfg(feature = "xml")]
fn xml_add_nvpair(elem: &mut Element, id: &str, name: &str, value: &str) {
    let nvpair = elem.append_new_child("nvpair");
    nvpair
        .set_attr("id", format!("{}-{}", &id, name))
        .set_attr("name", name)
        .set_attr("value", value);
}

pub fn attribute_extend(
    attributes: &mut Vec<Nvpair>,
    id: impl Into<String>,
    nvpairs: BTreeMap<String, String>,
) {
    let id = id.into();

    if let Some(attr) = attributes.first_mut() {
        // @@ search for id == attr.id?
        attr.nvpairs.extend(nvpairs);
    } else {
        let nvpair = Nvpair {
            id,
            nvpairs,
            ..Default::default()
        };
        attributes.push(nvpair);
    }
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("{0} Missing {1}")]
    MissingRequiredElement(String, String),
    #[error("{0} has invalid value {2} for element {1}")]
    InvalidValue(String, String, String),
    #[error("{0} failed to parse {1}")]
    ParseError(String, String),
}

impl Error {
    fn invalid(t: impl Into<String>, e: impl Into<String>, v: impl Into<String>) -> Self {
        Self::InvalidValue(t.into(), e.into(), v.into())
    }
    fn parse(t: impl Into<String>, v: impl Into<String>) -> Self {
        Self::ParseError(t.into(), v.into())
    }
    fn missing(t: impl Into<String>, v: impl Into<String>) -> Self {
        Self::ParseError(t.into(), v.into())
    }
}

trait ToCrmsh {
    /// Output crm shell configuration for object
    fn to_crmsh(&self) -> String;

    /// Output crm shell configuration for object (ignore id if same)
    fn to_crmsh_wo_id(&self, id: &str) -> String {
        let _ = id;
        self.to_crmsh()
    }
}

/// c.f. constraint-3.5.rng enum is named "attribute-actions"
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AttributeActions {
    Start,
    Promote,
    Demote,
    Stop,
}

impl fmt::Display for AttributeActions {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self {
            AttributeActions::Demote => write!(f, "demote"),
            AttributeActions::Promote => write!(f, "promote"),
            AttributeActions::Start => write!(f, "start"),
            AttributeActions::Stop => write!(f, "stop"),
        }
    }
}

impl ToCrmsh for Option<AttributeActions> {
    // when optional these appear as modifiers to resources <rsc>[:<ACTION>]
    fn to_crmsh(&self) -> String {
        match self {
            Some(a) => format!(":{}", a),
            None => "".to_string(),
        }
    }
}

impl TryFrom<&str> for AttributeActions {
    type Error = Error;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        match s.to_lowercase().trim() {
            "demote" => Ok(AttributeActions::Demote),
            "promote" => Ok(AttributeActions::Promote),
            "start" => Ok(AttributeActions::Start),
            "stop" => Ok(AttributeActions::Stop),
            e => Err(Error::parse("AttributeActions", e)),
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum BooleanOp {
    And,
    Or,
}
impl fmt::Display for BooleanOp {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self {
            BooleanOp::And => write!(f, "and"),
            BooleanOp::Or => write!(f, "or"),
        }
    }
}

impl Default for BooleanOp {
    fn default() -> Self {
        BooleanOp::And
    }
}

impl ToCrmsh for Option<BooleanOp> {
    fn to_crmsh(&self) -> String {
        match self {
            Some(op) => format!(" {}", op),
            None => format!(" {}", BooleanOp::default()),
        }
    }
}

impl TryFrom<&str> for BooleanOp {
    type Error = Error;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        match s.to_lowercase().trim() {
            "and" => Ok(BooleanOp::And),
            "or" => Ok(BooleanOp::Or),
            e => Err(Error::parse("BooleanOp", e)),
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Clone {
    pub id: String,
    pub instance_attributes: Vec<Nvpair>,
    pub meta_attributes: Vec<Nvpair>,
    pub item: PrimitiveOrGroup,
}

// Top Level
impl ToCrmsh for Clone {
    fn to_crmsh(&self) -> String {
        format!(
            "{}clone {} {}{}{}\n",
            self.item.to_crmsh(),
            self.id,
            self.item.id(),
            nvlist_or_none("meta", &self.meta_attributes, &self.id, "meta_attributes"),
            nvlist_or_none(
                "params",
                &self.instance_attributes,
                &self.id,
                "instance_attributes"
            ),
        )
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for Clone {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        Ok(Clone {
            id: elem
                .get_attr("id")
                .ok_or_else(|| Error::missing("Clone", "id"))?
                .to_string(),
            item: elem
                .children()
                .find(|c| matches!(c.tag().name(), "primitive" | "group"))
                .map(PrimitiveOrGroup::try_from)
                .ok_or_else(|| Error::missing("Clone", "primitive/group"))??,
            instance_attributes: elem
                .find_all("instance_attributes")
                .map(Nvpair::try_from)
                .collect::<Result<Vec<_>, Self::Error>>()?,
            meta_attributes: elem
                .find_all("meta_attributes")
                .map(Nvpair::try_from)
                .collect::<Result<Vec<_>, Self::Error>>()?,
        })
    }
}
#[cfg(feature = "xml")]
impl From<&Clone> for Element {
    fn from(clone: &Clone) -> Self {
        let mut elem = Element::new("clone");

        elem.set_attr("id", &clone.id);

        for (i, e) in clone.instance_attributes.iter().enumerate() {
            e.element_append(&mut elem, &clone.id, "instance_attributes", i);
        }
        for (i, e) in clone.meta_attributes.iter().enumerate() {
            e.element_append(&mut elem, &clone.id, "meta_attributes", i);
        }
        elem.append_child((&clone.item).into());

        elem
    }
}

#[cfg(feature = "xml")]
impl From<Clone> for Element {
    fn from(clone: Clone) -> Self {
        (&clone).into()
    }
}

/// Information about pacemaker resource agents
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Constraint {
    Colocation {
        id: String,
        rsc: String,
        with_rsc: String,
        score: Score,
    },
    Location {
        id: String,
        rsc: String,
        rons: RuleOrNodeScore,
        resource_discovery: Option<ResourceDiscovery>,
    },
    Order {
        id: String,
        first: String,
        first_action: Option<AttributeActions>,
        then: String,
        then_action: Option<AttributeActions>,
        // While the documentation only lists Kind the xml schema
        // (constraints-3.5.rng) shows Kind or Score being valid
        kind: Option<KindOrScore>,
        // symmetrical: bool,
        // require_all: bool
    },
    Ticket {
        id: String,
        rsc: String,
        ticket: String,
        loss_policy: Option<LossPolicy>,
    },
}

// Top Level
impl ToCrmsh for Constraint {
    fn to_crmsh(&self) -> String {
        match self {
            Constraint::Colocation {
                id,
                rsc,
                with_rsc,
                score,
            } => {
                format!(
                    "colocation {} {} {} {}\n",
                    id,
                    score.to_crmsh(),
                    rsc,
                    with_rsc
                )
            }
            Constraint::Location {
                id,
                rsc,
                rons,
                resource_discovery,
            } => {
                format!(
                    "location {} {}{} {}\n",
                    id,
                    rsc,
                    arg_or_none("resource-discovery", resource_discovery),
                    rons.to_crmsh_wo_id(&subid(id, "rule", 0))
                )
            }
            Constraint::Order {
                id,
                first,
                first_action,
                then,
                then_action,
                kind,
            } => {
                format!(
                    "order {}{} {}{} {}{}\n",
                    id,
                    kind.to_crmsh(),
                    first,
                    first_action.to_crmsh(),
                    then,
                    then_action.to_crmsh()
                )
            }
            Constraint::Ticket {
                id,
                rsc,
                ticket,
                loss_policy,
            } => {
                format!(
                    "rsc_ticket {} {}: {}{}\n",
                    id,
                    ticket,
                    rsc,
                    loss_policy.to_crmsh()
                )
            }
        }
    }
}

#[cfg(feature = "xml")]
impl From<&Constraint> for Element {
    fn from(con: &Constraint) -> Self {
        match con {
            Constraint::Colocation {
                id,
                rsc,
                with_rsc,
                score,
            } => {
                let mut con = Element::new("rsc_colocation");
                con.set_attr("id", id)
                    .set_attr("rsc", rsc)
                    .set_attr("with-rsc", with_rsc)
                    .set_attr("score", score.to_string());
                con
            }
            Constraint::Location {
                id,
                rsc,
                rons,
                resource_discovery,
            } => {
                let mut con = Element::new("rsc_location");
                con.set_attr("id", id).set_attr("rsc", rsc);
                if let Some(rd) = resource_discovery {
                    con.set_attr("resource-discovery", rd.to_string());
                }
                rons.element_append(&mut con);
                con
            }
            Constraint::Order {
                id,
                first,
                first_action,
                then,
                then_action,
                kind,
            } => {
                let mut con = Element::new("rsc_order");
                match kind {
                    Some(KindOrScore::Kind(kind)) => {
                        con.set_attr("kind", kind.to_string());
                    }
                    Some(KindOrScore::Score(score)) => {
                        con.set_attr("score", score.to_string());
                    }
                    None => (),
                }
                con.set_attr("id", id)
                    .set_attr("first", first)
                    .set_attr("then", then);
                if let Some(action) = first_action {
                    con.set_attr("first-action", action.to_string());
                }
                if let Some(action) = then_action {
                    con.set_attr("then-action", action.to_string());
                }
                con
            }
            Constraint::Ticket {
                id,
                rsc,
                ticket,
                loss_policy,
            } => {
                let mut con = Element::new("rsc_ticket");
                con.set_attr("id", id)
                    .set_attr("rsc", rsc)
                    .set_attr("ticket", ticket);
                if let Some(policy) = loss_policy {
                    con.set_attr("loss-policy", policy.to_string());
                }
                con
            }
        }
    }
}

#[cfg(feature = "xml")]
impl From<Constraint> for Element {
    fn from(con: Constraint) -> Self {
        (&con).into()
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for Constraint {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        let id = elem
            .get_attr("id")
            .ok_or_else(|| Error::missing("Constraint", "id"))?
            .to_string();
        match elem.tag().name() {
            "rsc_location" => Ok(Constraint::Location {
                id,
                rsc: elem
                    .get_attr("rsc")
                    .ok_or_else(|| Error::missing("Constraint::Location", "resource"))?
                    .to_string(),
                resource_discovery: elem
                    .get_attr("resource-discovery")
                    .map(ResourceDiscovery::try_from)
                    .transpose()?,
                rons: RuleOrNodeScore::try_from(elem)?,
            }),
            "rsc_colocation" => Ok(Constraint::Colocation {
                id,
                rsc: elem
                    .get_attr("rsc")
                    .ok_or_else(|| Error::missing("Constraint::Colocation", "resource"))?
                    .to_string(),
                with_rsc: elem
                    .get_attr("with-rsc")
                    .ok_or_else(|| Error::missing("Constraint::Colocation", "with-resource"))?
                    .to_string(),
                score: elem
                    .get_attr("score")
                    .map(Score::try_from)
                    .ok_or_else(|| Error::missing("Constraint::Colocation", "score"))??,
            }),
            "rsc_order" => Ok(Constraint::Order {
                id,
                kind: {
                    if let Some(score) = elem.get_attr("score") {
                        Some(KindOrScore::Score(Score::try_from(score)?))
                    } else if let Some(kind) = elem.get_attr("kind") {
                        Some(KindOrScore::Kind(OrderingKind::try_from(kind)?))
                    } else {
                        None
                    }
                },
                first: elem
                    .get_attr("first")
                    .ok_or_else(|| Error::missing("Constraint::Order", "first"))?
                    .to_string(),
                then: elem
                    .get_attr("then")
                    .ok_or_else(|| Error::missing("Constraint::Order", "then"))?
                    .to_string(),
                first_action: elem
                    .get_attr("first-action")
                    .map(AttributeActions::try_from)
                    .transpose()?,
                then_action: elem
                    .get_attr("then-action")
                    .map(AttributeActions::try_from)
                    .transpose()?,
            }),
            "rsc_ticket" => Ok(Constraint::Ticket {
                id,
                rsc: elem
                    .get_attr("rsc")
                    .ok_or_else(|| Error::missing("Constraint::Ticket", "resource"))?
                    .to_string(),
                ticket: elem
                    .get_attr("ticket")
                    .ok_or_else(|| Error::missing("Constraint::Ticket", "ticket"))?
                    .to_string(),
                loss_policy: elem
                    .get_attr("loss-policy")
                    .map(LossPolicy::try_from)
                    .transpose()?,
            }),
            e => Err(Error::parse("Constraint", e)),
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum ExpressionOp {
    Lt,
    Gt,
    Lte,
    Gte,
    Eq,
    Ne,
    Defined,
    NotDefined,
}

impl Default for ExpressionOp {
    fn default() -> Self {
        ExpressionOp::Defined
    }
}

impl fmt::Display for ExpressionOp {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self {
            ExpressionOp::Lt => write!(f, "lt"),
            ExpressionOp::Gt => write!(f, "gt"),
            ExpressionOp::Lte => write!(f, "lte"),
            ExpressionOp::Gte => write!(f, "gte"),
            ExpressionOp::Eq => write!(f, "eq"),
            ExpressionOp::Ne => write!(f, "ne"),
            ExpressionOp::Defined => write!(f, "defined"),
            ExpressionOp::NotDefined => write!(f, "not_defined"),
        }
    }
}

impl TryFrom<&str> for ExpressionOp {
    type Error = Error;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        match s.to_lowercase().trim() {
            "lt" => Ok(ExpressionOp::Lt),
            "gt" => Ok(ExpressionOp::Gt),
            "lte" => Ok(ExpressionOp::Lte),
            "gte" => Ok(ExpressionOp::Gte),
            "eq" => Ok(ExpressionOp::Eq),
            "ne" => Ok(ExpressionOp::Ne),
            "defined" => Ok(ExpressionOp::Defined),
            "not_defined" => Ok(ExpressionOp::NotDefined),
            e => Err(Error::parse("ExpressionOp", e)),
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Group {
    pub id: String,
    pub instance_attributes: Vec<Nvpair>,
    pub meta_attributes: Vec<Nvpair>,
    pub primitives: Vec<Primitive>,
}

// Top Level
impl ToCrmsh for Group {
    fn to_crmsh(&self) -> String {
        let mut output: Vec<String> = self.primitives.iter().map(|p| p.to_crmsh()).collect();

        output.push(format!(
            "group {} {}{}{}\n",
            self.id,
            self.primitives
                .iter()
                .map(|p| p.id.as_str())
                .collect::<Vec<_>>()
                .join(" "),
            nvlist_or_none("meta", &self.meta_attributes, &self.id, "meta_attributes"),
            nvlist_or_none(
                "params",
                &self.instance_attributes,
                &self.id,
                "instance_attributes"
            ),
        ));
        output.join("")
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for Group {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        Ok(Group {
            id: elem
                .get_attr("id")
                .ok_or_else(|| Error::missing("Group", "id"))?
                .to_string(),
            instance_attributes: elem
                .find_all("instance_attributes")
                .map(Nvpair::try_from)
                .collect::<Result<Vec<_>, Self::Error>>()?,
            meta_attributes: elem
                .find_all("meta_attributes")
                .map(Nvpair::try_from)
                .collect::<Result<Vec<_>, Self::Error>>()?,
            primitives: elem
                .find_all("primitive")
                .map(Primitive::try_from)
                .collect::<Result<Vec<Primitive>, Self::Error>>()?,
        })
    }
}

#[cfg(feature = "xml")]
impl From<&Group> for Element {
    fn from(grp: &Group) -> Self {
        let mut elem = Element::new("group");
        elem.set_attr("id", &grp.id);

        for (i, e) in grp.instance_attributes.iter().enumerate() {
            e.element_append(&mut elem, &grp.id, "instance_attributes", i);
        }
        for (i, e) in grp.meta_attributes.iter().enumerate() {
            e.element_append(&mut elem, &grp.id, "meta_attributes", i);
        }
        for p in &grp.primitives {
            elem.append_child(p.into());
        }

        elem
    }
}

#[cfg(feature = "xml")]
impl From<Group> for Element {
    fn from(res: Group) -> Self {
        (&res).into()
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum KindOrScore {
    Kind(OrderingKind),
    Score(Score),
}

impl ToCrmsh for KindOrScore {
    fn to_crmsh(&self) -> String {
        match self {
            KindOrScore::Kind(k) => k.to_crmsh(),
            KindOrScore::Score(s) => s.to_crmsh(),
        }
    }
}

impl ToCrmsh for Option<KindOrScore> {
    fn to_crmsh(&self) -> String {
        match &self {
            Some(s) => format!(" {}", s.to_crmsh()),
            None => "".to_string(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LossPolicy {
    Stop,
    Demote,
    Fence,
    Freeze,
}

impl fmt::Display for LossPolicy {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self {
            LossPolicy::Stop => write!(f, "stop"),
            LossPolicy::Demote => write!(f, "demote"),
            LossPolicy::Fence => write!(f, "fence"),
            LossPolicy::Freeze => write!(f, "freeze"),
        }
    }
}

impl ToCrmsh for Option<LossPolicy> {
    fn to_crmsh(&self) -> String {
        arg_or_none("loss-policy", self)
    }
}

impl TryFrom<&str> for LossPolicy {
    type Error = Error;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        match s.to_lowercase().trim() {
            "stop" => Ok(LossPolicy::Stop),
            "demote" => Ok(LossPolicy::Demote),
            "fence" => Ok(LossPolicy::Fence),
            "freeze" => Ok(LossPolicy::Freeze),
            e => Err(Error::parse("LossPolicy", e)),
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Node {
    pub id: String,
    pub uname: String,
    // pub type: Option<enum(member, ping, remote)>
    // pub description: Option<String>,
    pub score: Option<Score>,
    pub instance_attributes: Vec<Nvpair>,
    pub utilization: Vec<Nvpair>,
}

// Top Level
impl ToCrmsh for Node {
    fn to_crmsh(&self) -> String {
        format!(
            "node {}{}{}\n",
            self.uname,
            nvlist_or_none(
                "attributes",
                &self.instance_attributes,
                &self.id,
                "instance_attributes"
            ),
            nvlist_or_none("utilization", &self.utilization, &self.id, "utilization"),
        )
    }
}

#[derive(Debug, Clone, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Nvpair {
    pub id: String,
    pub rule: Option<Rule>,
    pub nvpairs: BTreeMap<String, String>,
    pub score: Option<Score>,
}

impl ToCrmsh for Nvpair {
    fn to_crmsh(&self) -> String {
        if self.nvpairs.is_empty() {
            return "".to_string();
        }
        format!(
            "{}{}{} {}",
            idspec(&self.id),
            self.score.to_crmsh(),
            self.rule.to_crmsh_wo_id(&subid(&self.id, "rule", 0)),
            self.nvpairs
                .iter()
                .map(|(k, v)| format!("{}={}", k, qvalue(v)))
                .collect::<Vec<String>>()
                .join(" ")
        )
    }
    fn to_crmsh_wo_id(&self, id: &str) -> String {
        if self.nvpairs.is_empty() {
            return "".to_string();
        }
        if id != self.id {
            self.to_crmsh()
        } else {
            format!(
                "{}{} {}",
                self.score.to_crmsh(),
                self.rule.to_crmsh_wo_id(&subid(&self.id, "rule", 0)),
                self.nvpairs
                    .iter()
                    .map(|(k, v)| format!("{}={}", k, qvalue(v)))
                    .collect::<Vec<String>>()
                    .join(" ")
            )
        }
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for Nvpair {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        Ok(Nvpair {
            id: elem.get_attr("id").unwrap_or_default().to_string(),
            rule: elem.find("rule").map(Rule::try_from).transpose()?,
            score: elem.get_attr("score").map(Score::try_from).transpose()?,
            nvpairs: elem
                .find_all("nvpair")
                .map(|nv| {
                    (
                        nv.get_attr("name").unwrap_or_default().to_string(),
                        nv.get_attr("value").unwrap_or_default().to_string(),
                    )
                })
                .collect(),
        })
    }
}

#[cfg(feature = "xml")]
impl Nvpair {
    /// tag is Element tag name
    fn element_append(&self, xml: &mut Element, parentid: &str, tag: &str, index: usize) {
        let id = if !self.id.is_empty() {
            self.id.to_string()
        } else {
            subid(parentid, tag, index)
        };

        let attr = xml.append_new_child(tag);
        attr.set_attr("id", &id);
        if let Some(s) = &self.score {
            attr.set_attr("score", s.to_string());
        }
        if let Some(r) = &self.rule {
            r.element_append(attr);
        }
        for (k, v) in self.nvpairs.iter() {
            xml_add_nvpair(attr, &id, k, v);
        }
    }
}

/// on-fail argument for Operation
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum OnFail {
    Ignore,
    Block,
    Demote,
    Stop,
    Restart,
    Standby,
    Fence,
    RestartContainer,
}

impl fmt::Display for OnFail {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            OnFail::Ignore => write!(f, "ignore"),
            OnFail::Block => write!(f, "block"),
            OnFail::Demote => write!(f, "demote"),
            OnFail::Stop => write!(f, "stop"),
            OnFail::Restart => write!(f, "restart"),
            OnFail::Standby => write!(f, "standby"),
            OnFail::Fence => write!(f, "fence"),
            OnFail::RestartContainer => write!(f, "restart-container"),
        }
    }
}

impl ToCrmsh for Option<OnFail> {
    fn to_crmsh(&self) -> String {
        arg_or_none("on-fail", self)
    }
}

impl TryFrom<&str> for OnFail {
    type Error = Error;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        match s.to_lowercase().trim() {
            "ignore" => Ok(OnFail::Ignore),
            "block" => Ok(OnFail::Block),
            "demote" => Ok(OnFail::Demote),
            "stop" => Ok(OnFail::Stop),
            "restart" => Ok(OnFail::Restart),
            "standby" => Ok(OnFail::Standby),
            "fence" => Ok(OnFail::Fence),
            "restart-container" => Ok(OnFail::RestartContainer),
            e => Err(Error::parse("OnFail", e)),
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Op {
    pub interval: String,
    pub timeout: Option<String>,
    pub record_pending: Option<bool>,
    pub on_fail: Option<OnFail>,
}

impl Default for Op {
    fn default() -> Self {
        Self {
            interval: "0".to_string(),
            timeout: None,
            record_pending: None,
            on_fail: None,
        }
    }
}

// This is most useful with op_or_none()
impl ToCrmsh for Op {
    fn to_crmsh(&self) -> String {
        format!(
            "interval={}{}{}{}",
            self.interval,
            arg_or_none("record-pending", &self.record_pending),
            self.on_fail.to_crmsh(),
            arg_or_none("timeout", &self.timeout)
        )
    }
}

#[cfg(feature = "xml")]
impl Op {
    fn element_append(&self, xml: &mut Element, opname: &str) {
        if &self.interval == "0" && self.timeout.is_none() {
            return;
        }

        let id = xml
            .get_attr("id")
            .expect("Op::element_append(): Element must have id set")
            .to_string();
        let op = xml.append_new_child("op");

        op.set_attr("name", opname);
        if &self.interval != "0" {
            op.set_attr(
                "id",
                format!("{}-{}-interval-{}", id, opname, self.interval),
            )
            .set_attr("interval", &self.interval);
        } else {
            // Interval is ALWAYS required
            op.set_attr("interval", "0");
        }
        if let Some(value) = &self.timeout {
            op.set_attr("id", format!("{}-{}-timeout-{}", id, opname, value))
                .set_attr("timeout", value);
        }
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for Op {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        Ok(Op {
            interval: elem
                .get_attr("interval")
                .map(|i| if i == "0s" { "0" } else { i })
                .ok_or_else(|| Error::missing("Op", "interval"))?
                .to_string(),
            timeout: elem.get_attr("timeout").map(str::to_string),
            record_pending: elem
                .get_attr("record-pending")
                .map(|s| {
                    s.parse()
                        .map_err(|_| Error::invalid("Op", "record-pending", s))
                })
                .transpose()?,
            on_fail: elem.get_attr("on-fail").map(OnFail::try_from).transpose()?,
        })
    }
}

#[derive(Debug, Clone, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Operations {
    // pub id: Option<String>,
    // Time to wait for Resource to start
    pub start: Option<Op>,
    // Time of monitor interval
    pub monitor: Option<Op>,
    // Time to wait for Resource to stop
    pub stop: Option<Op>,
}

impl Operations {
    pub fn new(
        start: impl Into<Option<String>>,
        monitor: impl Into<Option<String>>,
        stop: impl Into<Option<String>>,
    ) -> Self {
        Self {
            start: start.into().map(|s| Op {
                timeout: Some(s),
                ..Default::default()
            }),
            monitor: monitor.into().map(|s| Op {
                interval: s,
                ..Default::default()
            }),
            stop: stop.into().map(|s| Op {
                timeout: Some(s),
                ..Default::default()
            }),
        }
    }

    pub fn is_any_some(&self) -> bool {
        self.start.is_some() || self.stop.is_some() || self.monitor.is_some()
    }
}

impl ToCrmsh for Operations {
    fn to_crmsh(&self) -> String {
        format!(
            "{}{}{}",
            op_or_none("start", &self.start),
            op_or_none("monitor", &self.monitor),
            op_or_none("stop", &self.stop),
        )
    }
}

#[cfg(feature = "xml")]
impl Operations {
    pub fn element_append(&self, xml: &mut Element) {
        if !self.is_any_some() {
            return;
        }
        let ops = xml.append_new_child("operations");
        if let Some(op) = &self.start {
            op.element_append(ops, "start");
        }
        if let Some(op) = &self.stop {
            op.element_append(ops, "stop");
        }
        if let Some(op) = &self.monitor {
            op.element_append(ops, "monitor");
        }
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for Operations {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        let mut ops: BTreeMap<&str, Op> = elem
            .find_all("op")
            .map(|e| {
                Ok((
                    e.get_attr("name")
                        .ok_or_else(|| Error::missing("Op", "name"))?,
                    Op::try_from(e)?,
                ))
            })
            .collect::<Result<BTreeMap<_, _>, Self::Error>>()?;

        Ok(Operations {
            start: ops.remove("start"),
            monitor: ops.remove("monitor"),
            stop: ops.remove("stop"),
        })
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum OrderingKind {
    Mandatory,
    Optional,
    Serialize,
}

impl fmt::Display for OrderingKind {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        f.pad(&format!("{:?}", self))
    }
}

impl ToCrmsh for OrderingKind {
    fn to_crmsh(&self) -> String {
        format!("{}:", self)
    }
}

impl TryFrom<&str> for OrderingKind {
    type Error = Error;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        match s.to_lowercase().trim() {
            "mandatory" => Ok(OrderingKind::Mandatory),
            "optional" => Ok(OrderingKind::Optional),
            "serialize" => Ok(OrderingKind::Serialize),
            e => Err(Error::parse("OrderingKind", e)),
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Primitive {
    pub id: String,
    pub agent: ResourceAgentOrTemplate,
    pub instance_attributes: Vec<Nvpair>,
    pub meta_attributes: Vec<Nvpair>,
    pub ops: Operations,
    pub utilization: Vec<Nvpair>,
}

impl Primitive {
    pub fn new(
        id: impl Into<String>,
        agent: ResourceAgent,
        ops: impl Into<Option<Operations>>,
    ) -> Self {
        Primitive {
            id: id.into(),
            agent: ResourceAgentOrTemplate::ResourceAgent(agent),
            instance_attributes: Vec::new(),
            meta_attributes: Vec::new(),
            utilization: Vec::new(),
            ops: ops.into().unwrap_or_default(),
        }
    }
}

// Top Level
impl ToCrmsh for Primitive {
    fn to_crmsh(&self) -> String {
        format!(
            "primitive {} {}{}{}{}{}\n",
            self.id,
            self.agent.to_crmsh(),
            nvlist_or_none(
                "params",
                &self.instance_attributes,
                &self.id,
                "instance_attributes"
            ),
            nvlist_or_none("meta", &self.meta_attributes, &self.id, "meta_attributes"),
            nvlist_or_none(
                "utilization",
                &self.meta_attributes,
                &self.id,
                "utilization"
            ),
            self.ops.to_crmsh(),
        )
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for Primitive {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        Ok(Primitive {
            id: elem
                .get_attr("id")
                .ok_or_else(|| Error::missing("Primitive", "id"))?
                .to_string(),
            agent: ResourceAgentOrTemplate::try_from(elem)?,
            instance_attributes: elem
                .find_all("instance_attributes")
                .map(Nvpair::try_from)
                .collect::<Result<Vec<_>, Self::Error>>()?,
            meta_attributes: elem
                .find_all("meta_attributes")
                .map(Nvpair::try_from)
                .collect::<Result<Vec<_>, Self::Error>>()?,
            utilization: elem
                .find_all("utilization")
                .map(Nvpair::try_from)
                .collect::<Result<Vec<_>, Self::Error>>()?,
            ops: elem
                .find("operations")
                .map(Operations::try_from)
                .transpose()?
                .unwrap_or_default(),
        })
    }
}

#[cfg(feature = "xml")]
impl From<&Primitive> for Element {
    fn from(prim: &Primitive) -> Self {
        let mut elem = Element::new("primitive");
        elem.set_attr("id", &prim.id);

        match &prim.agent {
            ResourceAgentOrTemplate::ResourceAgent(ra) => {
                elem.set_attr("class", &ra.standard)
                    .set_attr("type", &ra.ocftype);
                if let Some(provider) = &ra.provider {
                    elem.set_attr("provider", provider);
                }
            }
            ResourceAgentOrTemplate::Template(t) => {
                elem.set_attr("template", t);
            }
        }

        prim.ops.element_append(&mut elem);

        for (i, e) in prim.instance_attributes.iter().enumerate() {
            e.element_append(&mut elem, &prim.id, "instance_attributes", i);
        }
        for (i, e) in prim.meta_attributes.iter().enumerate() {
            e.element_append(&mut elem, &prim.id, "meta_attributes", i);
        }
        for (i, e) in prim.utilization.iter().enumerate() {
            e.element_append(&mut elem, &prim.id, "utilization", i);
        }

        elem
    }
}

#[cfg(feature = "xml")]
impl From<Primitive> for Element {
    fn from(res: Primitive) -> Self {
        (&res).into()
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum PrimitiveOrGroup {
    Primitive(Primitive),
    Group(Group),
}

impl PrimitiveOrGroup {
    pub fn id(&self) -> String {
        match self {
            PrimitiveOrGroup::Primitive(x) => x.id.to_string(),
            PrimitiveOrGroup::Group(x) => x.id.to_string(),
        }
    }
}

impl From<Group> for PrimitiveOrGroup {
    fn from(x: Group) -> Self {
        PrimitiveOrGroup::Group(x)
    }
}

impl From<Primitive> for PrimitiveOrGroup {
    fn from(x: Primitive) -> Self {
        PrimitiveOrGroup::Primitive(x)
    }
}

impl ToCrmsh for PrimitiveOrGroup {
    fn to_crmsh(&self) -> String {
        match self {
            PrimitiveOrGroup::Primitive(x) => x.to_crmsh(),
            PrimitiveOrGroup::Group(x) => x.to_crmsh(),
        }
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for PrimitiveOrGroup {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        match elem.tag().name() {
            "primitive" => Primitive::try_from(elem).map(|x| x.into()),
            "group" => Group::try_from(elem).map(|x| x.into()),
            e => Err(Error::parse("Primitive/Group", e)),
        }
    }
}
#[cfg(feature = "xml")]
impl From<&PrimitiveOrGroup> for Element {
    fn from(x: &PrimitiveOrGroup) -> Self {
        match x {
            PrimitiveOrGroup::Primitive(x) => x.into(),
            PrimitiveOrGroup::Group(x) => x.into(),
        }
    }
}

#[cfg(feature = "xml")]
impl From<PrimitiveOrGroup> for Element {
    fn from(x: PrimitiveOrGroup) -> Self {
        (&x).into()
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum Resource {
    Primitive(Primitive),
    Template(Template),
    Group(Group),
    Clone(Clone),
    // The following two items are unimplemented resource types:
    // Master
    // Bundle
}

impl Resource {
    pub fn id(&self) -> String {
        match self {
            Resource::Primitive(x) => x.id.to_string(),
            Resource::Template(x) => x.id.to_string(),
            Resource::Group(x) => x.id.to_string(),
            Resource::Clone(x) => x.id.to_string(),
        }
    }

    pub fn set_target_role(&mut self, role: &str) {
        let id = self.id();

        let meta = match self {
            Resource::Primitive(x) => &mut x.meta_attributes,
            Resource::Template(x) => &mut x.meta_attributes,
            Resource::Group(x) => &mut x.meta_attributes,
            Resource::Clone(x) => &mut x.meta_attributes,
        };

        let role: BTreeMap<_, _> = vec![("target-role", role)]
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();

        attribute_extend(meta, format!("{}-meta_attributes", id), role);
    }
}

impl ToCrmsh for Resource {
    fn to_crmsh(&self) -> String {
        match self {
            Resource::Primitive(x) => x.to_crmsh(),
            Resource::Template(x) => x.to_crmsh(),
            Resource::Group(x) => x.to_crmsh(),
            Resource::Clone(x) => x.to_crmsh(),
        }
    }
}

impl From<Clone> for Resource {
    fn from(x: Clone) -> Self {
        Resource::Clone(x)
    }
}

impl From<Group> for Resource {
    fn from(x: Group) -> Self {
        Resource::Group(x)
    }
}

impl From<Primitive> for Resource {
    fn from(x: Primitive) -> Self {
        Resource::Primitive(x)
    }
}

impl From<Template> for Resource {
    fn from(x: Template) -> Self {
        Resource::Template(x)
    }
}

#[cfg(feature = "xml")]
impl From<&Resource> for Element {
    fn from(res: &Resource) -> Self {
        match res {
            Resource::Primitive(x) => x.into(),
            Resource::Template(x) => x.into(),
            Resource::Group(x) => x.into(),
            Resource::Clone(x) => x.into(),
        }
    }
}

#[cfg(feature = "xml")]
impl From<Resource> for Element {
    fn from(res: Resource) -> Self {
        (&res).into()
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for Resource {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        match elem.tag().name() {
            "primitive" => Primitive::try_from(elem).map(|x| x.into()),
            "clone" => Clone::try_from(elem).map(|x| x.into()),
            "group" => Group::try_from(elem).map(|x| x.into()),
            "template" => Template::try_from(elem).map(|x| x.into()),
            e => Err(Error::parse("Resource", e)),
        }
    }
}

/// standard:provider:ocftype (e.g. ocf:heartbeat:ZFS, or stonith:fence_ipmilan)
#[derive(serde::Deserialize, serde::Serialize, PartialEq, Clone, Debug)]
pub struct ResourceAgent {
    // e.g. ocf, lsb, stonith, etc..
    pub standard: String,
    // e.g. heartbeat, lustre, chroma
    pub provider: Option<String>,
    // e.g. Lustre, ZFS
    pub ocftype: String,
}

impl ResourceAgent {
    pub fn new<'a>(
        standard: impl Into<Option<&'a str>>,
        provider: impl Into<Option<&'a str>>,
        ocftype: impl Into<Option<&'a str>>,
    ) -> Self {
        Self {
            standard: standard.into().map(str::to_string).unwrap_or_default(),
            provider: provider.into().map(str::to_string),
            ocftype: ocftype.into().map(str::to_string).unwrap_or_default(),
        }
    }
}

impl fmt::Display for ResourceAgent {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self.provider {
            Some(provider) => write!(f, "{}:{}:{}", self.standard, provider, self.ocftype),
            None => write!(f, "{}:{}", self.standard, self.ocftype),
        }
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for ResourceAgent {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        Ok(ResourceAgent {
            standard: elem
                .get_attr("class")
                .ok_or_else(|| Error::missing("ResourceAgent", "class"))?
                .to_string(),
            provider: elem.get_attr("provider").map(str::to_string),
            ocftype: elem
                .get_attr("type")
                .ok_or_else(|| Error::missing("ResourceAgent", "type"))?
                .to_string(),
        })
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum ResourceAgentOrTemplate {
    ResourceAgent(ResourceAgent),
    Template(String),
}

impl ToCrmsh for ResourceAgentOrTemplate {
    fn to_crmsh(&self) -> String {
        match self {
            ResourceAgentOrTemplate::ResourceAgent(ra) => ra.to_string(),
            ResourceAgentOrTemplate::Template(t) => format!("@{}", t),
        }
    }
}

impl From<ResourceAgent> for ResourceAgentOrTemplate {
    fn from(ra: ResourceAgent) -> Self {
        ResourceAgentOrTemplate::ResourceAgent(ra)
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for ResourceAgentOrTemplate {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        if let Some(s) = elem.get_attr("template") {
            Ok(ResourceAgentOrTemplate::Template(s.to_string()))
        } else {
            Ok(ResourceAgentOrTemplate::ResourceAgent(
                ResourceAgent::try_from(elem)?,
            ))
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum ResourceDiscovery {
    Always,
    Never,
    Exclusive,
}

impl fmt::Display for ResourceDiscovery {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self {
            ResourceDiscovery::Always => write!(f, "always"),
            ResourceDiscovery::Never => write!(f, "never"),
            ResourceDiscovery::Exclusive => write!(f, "exclusive"),
        }
    }
}
impl TryFrom<&str> for ResourceDiscovery {
    type Error = Error;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        match s.to_lowercase().trim() {
            "always" => Ok(ResourceDiscovery::Always),
            "never" => Ok(ResourceDiscovery::Never),
            "exclusive" => Ok(ResourceDiscovery::Exclusive),
            e => Err(Error::parse("ResourceDiscovery", e)),
        }
    }
}

#[derive(Debug, Clone, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Rule {
    pub id: String,
    pub score: ScoreOrAttribute,
    pub op: Option<BooleanOp>,
    pub role: Option<String>,
    // technically the following should:
    //   Vec<enum(expression, date_expression, rsc_expression, op_expression)>
    // but we only use "expression"
    pub expressions: Vec<RuleExpression>,
}

impl ToCrmsh for Rule {
    fn to_crmsh(&self) -> String {
        format!(
            "rule{}{}{}{}",
            idspec(&self.id),
            arg_or_none("$role", &self.role),
            self.score.to_crmsh(),
            self.expressions
                .iter()
                .enumerate()
                .map(|(index, re)| re.to_crmsh_wo_id(&subid(&self.id, "expression", index)))
                .collect::<Vec<String>>()
                .join(&self.op.to_crmsh())
        )
    }
    fn to_crmsh_wo_id(&self, id: &str) -> String {
        if id != self.id {
            self.to_crmsh()
        } else {
            format!(
                "rule{}{}{}",
                arg_or_none("$role", &self.role),
                self.score.to_crmsh(),
                self.expressions
                    .iter()
                    .enumerate()
                    .map(|(index, re)| re.to_crmsh_wo_id(&subid(&self.id, "expression", index)))
                    .collect::<Vec<String>>()
                    .join(&self.op.to_crmsh())
            )
        }
    }
}

impl ToCrmsh for Option<Rule> {
    fn to_crmsh(&self) -> String {
        match self {
            Some(s) => format!(" {}", s.to_crmsh()),
            None => "".to_string(),
        }
    }
    fn to_crmsh_wo_id(&self, id: &str) -> String {
        match self {
            Some(s) => format!(" {}", s.to_crmsh_wo_id(id)),
            None => "".to_string(),
        }
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for Rule {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        Ok(Rule {
            id: elem.get_attr("id").unwrap_or_default().to_string(),
            score: ScoreOrAttribute::try_from(elem)?,
            op: elem
                .get_attr("boolean-op")
                .map(BooleanOp::try_from)
                .transpose()?,
            role: elem.get_attr("role").map(|s| s.to_string()),
            expressions: elem
                .find_all("expression")
                .map(RuleExpression::try_from)
                .collect::<Result<Vec<_>, Self::Error>>()?,
        })
    }
}

#[cfg(feature = "xml")]
impl Rule {
    fn element_append(&self, xml: &mut Element) {
        let parentid = xml.get_attr("id").unwrap_or_default();
        let id = format!("{}-rule", parentid);

        let rule = xml.append_new_child("rule");
        rule.set_attr("id", &id);
        match &self.score {
            ScoreOrAttribute::Score(x) => rule.set_attr("score", x.to_string()),
            ScoreOrAttribute::Attribute(x) => rule.set_attr("score-attribute", x),
        };
        if let Some(op) = &self.op {
            rule.set_attr("boolean-op", op.to_string());
        }
        if let Some(r) = &self.role {
            rule.set_attr("role", r);
        }
        for (i, e) in self.expressions.iter().enumerate() {
            e.element_append(rule, &id, i);
        }
    }
}

#[derive(Debug, Clone, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct RuleExpression {
    id: String,
    attribute: String,
    operation: ExpressionOp,
    value: Option<String>,
    // unused entry: type: Option<enum(string, integer, number, version)> - default:string
    value_source: Option<ValueSource>,
}

impl ToCrmsh for RuleExpression {
    fn to_crmsh(&self) -> String {
        match &self.value {
            // Binary Operator
            Some(v) => format!(
                "{} {} {} {}{}",
                idspec(&self.id),
                self.attribute,
                self.operation,
                v,
                self.value_source.to_crmsh()
            ),
            // Unary Operator
            None => format!(
                "{} {} {}{}",
                idspec(&self.id),
                self.operation,
                self.attribute,
                self.value_source.to_crmsh()
            ),
        }
    }
    fn to_crmsh_wo_id(&self, id: &str) -> String {
        if id != self.id {
            self.to_crmsh()
        } else {
            match &self.value {
                // Binary Operator
                Some(v) => format!(
                    " {} {} {}{}",
                    self.attribute,
                    self.operation,
                    v,
                    self.value_source.to_crmsh()
                ),
                // Unary Operator
                None => format!(
                    " {} {}{}",
                    self.operation,
                    self.attribute,
                    self.value_source.to_crmsh()
                ),
            }
        }
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for RuleExpression {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        Ok(RuleExpression {
            id: elem.get_attr("id").unwrap_or_default().to_string(),
            attribute: elem
                .get_attr("attribute")
                .ok_or_else(|| Error::missing("RuleExpression", "attribute"))?
                .to_string(),
            operation: elem
                .get_attr("operation")
                .map(ExpressionOp::try_from)
                .transpose()?
                .ok_or_else(|| Error::missing("RuleExpression", "operation"))?,
            value: elem.get_attr("value").map(|s| s.to_string()),
            value_source: elem
                .get_attr("value-source")
                .map(ValueSource::try_from)
                .transpose()?,
        })
    }
}

#[cfg(feature = "xml")]
impl RuleExpression {
    /// tag is Element tag name
    fn element_append(&self, xml: &mut Element, parentid: &str, index: usize) {
        let id = if !self.id.is_empty() {
            self.id.to_string()
        } else {
            subid(parentid, "expression", index)
        };

        let expression = xml.append_new_child("expression");
        expression
            .set_attr("id", &id)
            .set_attr("operation", self.operation.to_string())
            .set_attr("attribute", &self.attribute);
        if let Some(v) = &self.value {
            expression.set_attr("value", v);
        }
        if let Some(v) = &self.value_source {
            expression.set_attr("value-source", v.to_string());
        }
    }
}

// This is for Constraint Location - Rule or Score+Node
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum RuleOrNodeScore {
    Rule(Rule),
    NodeScore { node: String, score: Score },
}

impl ToCrmsh for RuleOrNodeScore {
    fn to_crmsh(&self) -> String {
        match self {
            RuleOrNodeScore::Rule(rule) => rule.to_crmsh(),
            RuleOrNodeScore::NodeScore { node, score } => format!("{} {}", score.to_crmsh(), node),
        }
    }
    fn to_crmsh_wo_id(&self, id: &str) -> String {
        match self {
            RuleOrNodeScore::Rule(rule) => rule.to_crmsh_wo_id(id),
            RuleOrNodeScore::NodeScore { node, score } => format!("{} {}", score.to_crmsh(), node),
        }
    }
}

#[cfg(feature = "xml")]
impl RuleOrNodeScore {
    fn element_append(&self, xml: &mut Element) {
        match self {
            RuleOrNodeScore::Rule(rule) => rule.element_append(xml),
            RuleOrNodeScore::NodeScore { node, score } => {
                xml.set_attr("node", node)
                    .set_attr("score", score.to_string());
            }
        }
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for RuleOrNodeScore {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        if let Some(rule) = elem.find("rule") {
            Ok(RuleOrNodeScore::Rule(Rule::try_from(rule)?))
        } else {
            Ok(RuleOrNodeScore::NodeScore {
                node: elem
                    .get_attr("node")
                    .ok_or_else(|| Error::missing("Constraint", "node"))?
                    .to_string(),
                score: elem
                    .get_attr("score")
                    .map(Score::try_from)
                    .ok_or_else(|| Error::missing("Constraint", "score"))??,
            })
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Score {
    Infinity,
    Value(i32),
    NegInfinity,
}

impl fmt::Display for Score {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self {
            Score::Value(v) => write!(f, "{}", v),
            Score::Infinity => write!(f, "INFINITY"),
            Score::NegInfinity => write!(f, "-INFINITY"),
        }
    }
}

impl ToCrmsh for Score {
    fn to_crmsh(&self) -> String {
        match &self {
            Score::Value(v) => format!("{}:", v),
            Score::Infinity => "inf:".to_string(),
            Score::NegInfinity => "-inf:".to_string(),
        }
    }
}

impl ToCrmsh for Option<Score> {
    fn to_crmsh(&self) -> String {
        match &self {
            Some(s) => format!(" {}", s.to_crmsh()),
            None => "".to_string(),
        }
    }
}

impl TryFrom<&str> for Score {
    type Error = Error;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        if let Ok(score) = s.trim().parse::<i32>() {
            if score > INFINITY {
                Ok(Score::Infinity)
            } else if score < NEG_INFINITY {
                Ok(Score::NegInfinity)
            } else {
                Ok(Score::Value(score))
            }
        } else {
            match s.to_uppercase().trim() {
                "INFINITY" => Ok(Score::Infinity),
                "INF" => Ok(Score::Infinity),
                "-INFINITY" => Ok(Score::NegInfinity),
                "-INF" => Ok(Score::NegInfinity),
                e => Err(Error::parse("Score", e)),
            }
        }
    }
}

// Child of Rule struct
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum ScoreOrAttribute {
    Score(Score),
    Attribute(String),
}

impl Default for ScoreOrAttribute {
    fn default() -> Self {
        ScoreOrAttribute::Score(Score::Infinity)
    }
}

impl ToCrmsh for ScoreOrAttribute {
    fn to_crmsh(&self) -> String {
        match self {
            ScoreOrAttribute::Attribute(s) => format!(" {}:", s),
            // Rules that have Infinite score do not show (i.e. rules for attributes
            // in NV Lists, the Nvpair has a score, and this core is INIFINITY and not
            // used)
            ScoreOrAttribute::Score(Score::Infinity) => "".to_string(),
            ScoreOrAttribute::Score(s) => format!(" {}", s.to_crmsh()),
        }
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for ScoreOrAttribute {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        if let Some(s) = elem.get_attr("score").map(Score::try_from).transpose()? {
            Ok(ScoreOrAttribute::Score(s))
        } else if let Some(att) = elem.get_attr("score-attribute") {
            Ok(ScoreOrAttribute::Attribute(att.to_string()))
        } else {
            Err(Error::missing("Rule", "score and score-attribute"))
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Template {
    pub id: String,
    pub agent: ResourceAgent,
    pub instance_attributes: Vec<Nvpair>,
    pub meta_attributes: Vec<Nvpair>,
    pub ops: Operations,
    pub utilization: Vec<Nvpair>,
}

// Top Level
impl ToCrmsh for Template {
    fn to_crmsh(&self) -> String {
        format!(
            "rsc_template {} {}{}{}{}{}\n",
            self.id,
            self.agent.to_string(),
            nvlist_or_none(
                "params",
                &self.instance_attributes,
                &self.id,
                "instance_attributes"
            ),
            nvlist_or_none("meta", &self.meta_attributes, &self.id, "meta_attributes"),
            nvlist_or_none("utilization", &self.utilization, &self.id, "utilization"),
            self.ops.to_crmsh()
        )
    }
}

#[cfg(feature = "xml")]
impl TryFrom<&Element> for Template {
    type Error = Error;

    fn try_from(elem: &Element) -> Result<Self, Self::Error> {
        Ok(Template {
            id: elem
                .get_attr("id")
                .ok_or_else(|| Error::missing("Template", "id"))?
                .to_string(),
            agent: ResourceAgent::try_from(elem)?,
            instance_attributes: elem
                .find_all("instance_attributes")
                .map(Nvpair::try_from)
                .collect::<Result<Vec<_>, Self::Error>>()?,
            meta_attributes: elem
                .find_all("meta_attributes")
                .map(Nvpair::try_from)
                .collect::<Result<Vec<_>, Self::Error>>()?,
            utilization: elem
                .find_all("utilization")
                .map(Nvpair::try_from)
                .collect::<Result<Vec<_>, Self::Error>>()?,
            ops: elem
                .find("operations")
                .map(Operations::try_from)
                .transpose()?
                .unwrap_or_default(),
        })
    }
}

#[cfg(feature = "xml")]
impl From<&Template> for Element {
    fn from(temp: &Template) -> Self {
        let mut elem = Element::new("template");

        elem.set_attr("id", &temp.id)
            .set_attr("class", &temp.agent.standard)
            .set_attr("type", &temp.agent.ocftype);
        if let Some(provider) = &temp.agent.provider {
            elem.set_attr("provider", provider);
        }

        temp.ops.element_append(&mut elem);

        for (i, e) in temp.instance_attributes.iter().enumerate() {
            e.element_append(&mut elem, &temp.id, "instance_attributes", i);
        }
        for (i, e) in temp.meta_attributes.iter().enumerate() {
            e.element_append(&mut elem, &temp.id, "meta_attributes", i);
        }
        for (i, e) in temp.utilization.iter().enumerate() {
            e.element_append(&mut elem, &temp.id, "utilization", i);
        }

        elem
    }
}

#[cfg(feature = "xml")]
impl From<Template> for Element {
    fn from(temp: Template) -> Self {
        (&temp).into()
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum ValueSource {
    Literal,
    Param,
    Meta,
}

impl Default for ValueSource {
    fn default() -> Self {
        ValueSource::Literal
    }
}

impl fmt::Display for ValueSource {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self {
            ValueSource::Literal => write!(f, "literal"),
            ValueSource::Param => write!(f, "param"),
            ValueSource::Meta => write!(f, "meta"),
        }
    }
}

impl ToCrmsh for Option<ValueSource> {
    fn to_crmsh(&self) -> String {
        match self {
            None => "".to_string(),
            Some(vs) => format!(" {}", vs),
        }
    }
}

impl TryFrom<&str> for ValueSource {
    type Error = Error;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        match s.to_lowercase().trim() {
            "literal" => Ok(ValueSource::Literal),
            "param" => Ok(ValueSource::Param),
            "meta" => Ok(ValueSource::Meta),
            e => Err(Error::parse("ValueSource", e)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[cfg(feature = "xml")]
    use elementtree::Element;
    #[cfg(feature = "xml")]
    use std::{collections::BTreeMap, convert::TryFrom};

    #[test]
    fn test_resource_agent_3() {
        let ra = ResourceAgent::new("ocf", "heartbeat", "LVM");
        assert_eq!("ocf:heartbeat:LVM", &ra.to_string())
    }

    #[test]
    fn test_resource_agent_2() {
        let ra = ResourceAgent::new("stonith", None, "fence_ipmilan");
        assert_eq!("stonith:fence_ipmilan", &ra.to_string())
    }

    #[test]
    fn test_crmsh_resource_agent_or_template() {
        let rat = ResourceAgentOrTemplate::Template("xyzzy".to_string());
        assert_eq!("@xyzzy", &rat.to_crmsh())
    }

    #[test]
    #[cfg(feature = "xml")]
    fn test_fromxml_fence_chroma() {
        let testxml: &[u8] = include_bytes!("fixtures/primitive-chroma-stonith.xml");
        let e = Element::from_reader(testxml).unwrap();

        assert_eq!(
            Primitive::try_from(&e).unwrap(),
            Primitive::new(
                "st-fencing",
                ResourceAgent::new("stonith", None, "fence_chroma"),
                None
            ),
        );
    }

    #[test]
    #[cfg(feature = "xml")]
    fn test_fromxml_lustre_mgs() {
        let testxml: &[u8] = include_bytes!("fixtures/primitive-lustre-mgs.xml");
        let e = Element::from_reader(testxml).unwrap();

        let mut prim = Primitive::new(
            "MGS",
            ResourceAgent::new("ocf", "lustre", "Lustre"),
            Operations::new("300s".to_string(), "20s".to_string(), "300s".to_string()),
        );
        if let Some(ref mut mon) = prim.ops.monitor {
            mon.timeout = Some("300s".to_string());
        }

        let data: BTreeMap<_, _> = vec![
            (
                "target",
                "/dev/disk/by-id/scsi-36001405c20616f7b8b2492d8913a4d24",
            ),
            ("mountpoint", "/mnt/MGS"),
        ]
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect();

        prim.instance_attributes.push(Nvpair {
            id: "MGS-instance_attributes".to_string(),
            nvpairs: data,
            ..Default::default()
        });

        assert_eq!(Primitive::try_from(&e).unwrap(), prim);
    }

    #[test]
    #[cfg(feature = "xml")]
    fn test_fromxml_es_ost() {
        let testxml: &[u8] = include_bytes!("fixtures/primitive-es-ost.xml");
        let e = Element::from_reader(testxml).unwrap();

        let mut ost = Primitive::new(
            "ost0001-es01a",
            ResourceAgent::new("ocf", Some("ddn"), "lustre-server"),
            Operations::new("450".to_string(), "30".to_string(), "300".to_string()),
        );
        if let Some(ref mut mon) = ost.ops.monitor {
            mon.timeout = Some("300".to_string());
        }
        if let Some(ref mut x) = ost.ops.start {
            x.record_pending = Some(true);
        }
        if let Some(ref mut x) = ost.ops.stop {
            x.record_pending = Some(true);
        }

        let ia1: BTreeMap<_, _> = vec![("lustre_resource_type", "ost"), ("manage_directory", "1")]
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();

        let ia2: BTreeMap<_, _> = vec![
            ("device", "/dev/ddn/es01a_ost0001"),
            ("directory", "/lustre/es01a/ost0001"),
        ]
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect();
        let m1: BTreeMap<_, _> = vec![("priority", "0")]
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();
        let m2: BTreeMap<_, _> = vec![("zone", "AI400-006c")]
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();
        let u: BTreeMap<_, _> = vec![("lustre-object", "1")]
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();

        ost.instance_attributes = vec![
            Nvpair {
                id: "lustre-es01a-ost-instance_attributes".to_string(),
                nvpairs: ia1,
                ..Default::default()
            },
            Nvpair {
                id: "ost0001-es01a-instance_attributes".to_string(),
                nvpairs: ia2,
                ..Default::default()
            },
        ];
        ost.meta_attributes = vec![
            Nvpair {
                id: "lustre-es01a-ost-meta_attributes".to_string(),
                nvpairs: m1,
                ..Default::default()
            },
            Nvpair {
                id: "ost0001-es01a-meta_attributes".to_string(),
                nvpairs: m2,
                ..Default::default()
            },
        ];
        ost.utilization.push(Nvpair {
            id: "lustre-es01a-ost-utilization".to_string(),
            nvpairs: u,
            ..Default::default()
        });
        assert_eq!(Primitive::try_from(&e).unwrap(), ost);
    }

    #[test]
    #[cfg(feature = "xml")]
    fn test_xml_to_crmsh_clone() {
        let testxml: &[u8] = include_bytes!("fixtures/clone-es-sfa-home-vd.xml");
        let testcrm: String = include_str!("fixtures/clone-es-sfa-home-vd.crmsh").to_string();
        let e = Element::from_reader(testxml).unwrap();

        let r = Resource::try_from(&e).unwrap();

        assert_eq!(r.to_crmsh(), testcrm);
    }

    #[test]
    #[cfg(feature = "xml")]
    fn test_xml_to_crmsh_group() {
        let testxml: &[u8] = include_bytes!("fixtures/group-es-emf-docker.xml");
        let testcrm: String = include_str!("fixtures/group-es-emf-docker.crmsh").to_string();
        let e = Element::from_reader(testxml).unwrap();

        let r = Resource::try_from(&e).unwrap();

        assert_eq!(r.to_crmsh(), testcrm);
    }

    #[test]
    #[cfg(feature = "xml")]
    fn test_xml_to_crmsh_resource_template() {
        let testxml: &[u8] = include_bytes!("fixtures/resource-template.xml");
        let testcrm: String = include_str!("fixtures/resource-template.crmsh").to_string();
        let e = Element::from_reader(testxml).unwrap();

        let r = Resource::try_from(&e).unwrap();

        assert_eq!(r.to_crmsh(), testcrm);
    }

    #[test]
    #[cfg(feature = "xml")]
    fn test_xml_to_crmsh_constraint_location() {
        let testxml: &[u8] = include_bytes!("fixtures/constraint-location.xml");
        let testcrm: String = include_str!("fixtures/constraint-location.crmsh").to_string();
        let e = Element::from_reader(testxml).unwrap();

        let r = Constraint::try_from(&e).unwrap();

        assert_eq!(r.to_crmsh(), testcrm);
    }

    #[test]
    #[cfg(feature = "xml")]
    fn test_xml_to_crmsh_constraint_location_rule() {
        let testxml: &[u8] = include_bytes!("fixtures/constraint-location-rule.xml");
        let testcrm: String = include_str!("fixtures/constraint-location-rule.crmsh").to_string();
        let e = Element::from_reader(testxml).unwrap();

        let r = Constraint::try_from(&e).unwrap();

        assert_eq!(r.to_crmsh(), testcrm);
    }

    #[test]
    #[cfg(feature = "xml")]
    fn test_xml_to_crmsh_constraint_colocation() {
        let testxml: &[u8] = include_bytes!("fixtures/constraint-colocation.xml");
        let testcrm: String = include_str!("fixtures/constraint-colocation.crmsh").to_string();
        let e = Element::from_reader(testxml).unwrap();

        let r = Constraint::try_from(&e).unwrap();

        assert_eq!(r.to_crmsh(), testcrm);
    }

    #[test]
    #[cfg(feature = "xml")]
    fn test_xml_to_crmsh_constraint_order() {
        let testxml: &[u8] = include_bytes!("fixtures/constraint-order.xml");
        let testcrm: String = include_str!("fixtures/constraint-order.crmsh").to_string();
        let e = Element::from_reader(testxml).unwrap();

        let r = Constraint::try_from(&e).unwrap();

        assert_eq!(r.to_crmsh(), testcrm);
    }

    #[test]
    #[cfg(feature = "xml")]
    fn test_xml_to_crmsh_constraint_ticket() {
        let testxml: &[u8] = include_bytes!("fixtures/constraint-ticket.xml");
        let testcrm: String = include_str!("fixtures/constraint-ticket.crmsh").to_string();
        let e = Element::from_reader(testxml).unwrap();

        let r = Constraint::try_from(&e).unwrap();

        assert_eq!(r.to_crmsh(), testcrm);
    }

    #[test]
    fn test_crmsh_rule() {
        let rule = Rule {
            op: Some(BooleanOp::And),
            expressions: vec![
                RuleExpression {
                    attribute: "system-type".to_string(),
                    ..Default::default()
                },
                RuleExpression {
                    attribute: "system-type".to_string(),
                    operation: ExpressionOp::Eq,
                    value: Some("block".to_string()),
                    ..Default::default()
                },
            ],
            ..Default::default()
        };
        assert_eq!(
            "rule defined system-type and system-type eq block",
            &rule.to_crmsh()
        )
    }
}
