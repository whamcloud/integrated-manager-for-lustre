// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod req {
    use quick_xml::{
        events::{self, Event},
        Writer,
    };
    use std::io::Cursor;

    type EVs<'a> = Vec<events::Event<'a>>;

    pub(crate) fn decl<'a>(mut xs: EVs<'a>) -> EVs<'a> {
        xs.insert(
            0,
            Event::Decl(events::BytesDecl::new(b"1.0", Some(b"utf-8"), None)),
        );

        xs
    }

    /// The CIM element is the root element of every XML Document that is
    /// valid with respect to this schema.
    ///
    /// Each document takes one of two forms; it either contains a single
    /// MESSAGE element defining a CIM message (to be used in the HTTP
    /// mapping), or it contains a DECLARATION element used to declare a
    /// set of CIM objects.
    pub(crate) fn cim<'a>(cim_version: &str, dtd_version: &str, mut xs: EVs<'a>) -> EVs<'a> {
        xs.insert(
            0,
            Event::Start(
                events::BytesStart::borrowed_name(b"CIM").with_attributes(vec![
                    ("CIMVERSION", cim_version),
                    ("DTDVERSION", dtd_version),
                ]),
            ),
        );

        xs.push(Event::End(events::BytesEnd::borrowed(b"CIM")));

        xs
    }

    /// The MESSAGE element models a single CIM message.  This element is
    /// used as the basis for CIM Operation Messages and CIM Export
    /// Messages.
    pub(crate) fn message<'a>(id: &str, protocol_version: &str, mut xs: EVs<'a>) -> EVs<'a> {
        xs.insert(
            0,
            Event::Start(
                events::BytesStart::borrowed_name(b"MESSAGE")
                    .with_attributes(vec![("ID", id), ("PROTOCOLVERSION", protocol_version)]),
            ),
        );

        xs.push(Event::End(events::BytesEnd::borrowed(b"MESSAGE")));

        xs
    }

    /// The SIMPLEREQ element defines a Simple CIM Operation request.  It
    /// contains either a METHODCALL (extrinsic method) element or an
    /// IMETHODCALL (intrinsic method) element.
    pub(crate) fn simple_req<'a>(mut xs: EVs<'a>) -> EVs<'a> {
        let name = b"SIMPLEREQ";

        xs.insert(0, Event::Start(events::BytesStart::borrowed_name(name)));

        xs.push(Event::End(events::BytesEnd::borrowed(name)));

        xs
    }
    /// The IMETHODCALL element defines a single intrinsic method
    /// invocation.  It specifies the target local namespace, followed by
    /// zero or more IPARAMVALUE subelements as the parameter values to be
    /// passed to the method. If the RESPONSEDESTINATION element is
    /// specified, the intrinsic method call MUST be interpreted as an
    /// asynchronous method call.
    pub(crate) fn imethodcall<'a>(name: &str, mut xs: EVs<'a>) -> EVs<'a> {
        let el_name = b"IMETHODCALL";

        xs.insert(
            0,
            Event::Start(
                events::BytesStart::borrowed_name(el_name).with_attributes(vec![("NAME", name)]),
            ),
        );

        xs.push(Event::End(events::BytesEnd::borrowed(el_name)));

        xs
    }

    pub enum ParamValue {
        ClassName(String),
    }

    impl<'a> From<ParamValue> for Event<'a> {
        fn from(x: ParamValue) -> Self {
            match x {
                ParamValue::ClassName(s) => classname(&s),
            }
        }
    }

    /// The PARAMVALUE element defines a single method parameter value of non-array, non-reference type.
    /// If no VALUE subelement is present this indicates a NULL value.
    pub(crate) fn iparamvalue<'a>(name: &str, x: Event<'a>) -> EVs<'a> {
        let el_name = b"IPARAMVALUE";

        vec![
            Event::Start(
                events::BytesStart::borrowed_name(el_name).with_attributes(vec![("NAME", name)]),
            ),
            x,
            Event::End(events::BytesEnd::borrowed(el_name)),
        ]
    }

    /// The CLASSNAME element defines the qualifying name of a CIM Class.
    pub(crate) fn classname<'a>(name: &str) -> Event<'a> {
        Event::Empty(
            events::BytesStart::borrowed_name(b"CLASSNAME").with_attributes(vec![("NAME", name)]),
        )
    }

    /// The LOCALNAMESPACEPATH element is used to define a local Namespace
    /// path (one without a Host component). It consists of one or more
    /// NAMESPACE elements (one for each namespace in the path).
    pub(crate) fn local_namespace_path<'a>(mut xs: EVs<'a>) -> EVs<'a> {
        let el_name = b"LOCALNAMESPACEPATH";

        xs.insert(0, Event::Start(events::BytesStart::borrowed_name(el_name)));

        xs.push(Event::End(events::BytesEnd::borrowed(el_name)));

        xs
    }

    /// The NAMESPACE element is used to define a single Namespace
    /// component of a Namespace path.
    pub(crate) fn namespace<'a>(name: &str) -> Event<'a> {
        Event::Empty(
            events::BytesStart::borrowed_name(b"NAMESPACE").with_attributes(vec![("NAME", name)]),
        )
    }

    pub(crate) fn evs_to_bytes<'a>(xs: EVs<'a>) -> Result<Vec<u8>, quick_xml::Error> {
        let mut writer = Writer::new(Cursor::new(Vec::new()));

        for x in xs {
            writer.write_event(x)?;
        }

        Ok(writer.into_inner().into_inner())
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[test]
        fn test_build_imethodcall() {
            let xs = decl(cim(
                "2.0",
                "2.0",
                message(
                    "1001",
                    "1.0",
                    simple_req(imethodcall(
                        "EnumerateInstances",
                        vec![
                            local_namespace_path(vec![namespace("root"), namespace("ddn")]),
                            iparamvalue("ClassName", classname("DDN_SFAController")),
                        ]
                        .concat(),
                    )),
                ),
            ));

            let mut writer = Writer::new_with_indent(Cursor::new(Vec::new()), b' ', 4);

            for x in xs {
                writer.write_event(x).unwrap();
            }

            let xs = writer.into_inner().into_inner();

            insta::assert_display_snapshot!(String::from_utf8_lossy(&xs));
        }
    }
}

pub mod resp {
    #[derive(Debug, serde::Deserialize, PartialEq)]
    pub struct ValueArray {
        #[serde(rename = "$value", default)]
        inner: Vec<String>,
    }

    #[derive(Debug, serde::Deserialize, PartialEq)]
    pub enum Property {
        #[serde(rename = "PROPERTY")]
        Single {
            #[serde(rename = "NAME")]
            name: Option<String>,
            #[serde(rename = "TYPE")]
            prop_type: String,
            #[serde(rename = "VALUE")]
            value: Option<String>,
        },
        #[serde(rename = "PROPERTY.ARRAY")]
        Multiple {
            #[serde(rename = "NAME")]
            name: Option<String>,
            #[serde(rename = "TYPE")]
            prop_type: String,
            #[serde(rename = "VALUE.ARRAY")]
            values: ValueArray,
        },
    }

    impl Property {
        pub fn name(&self) -> Option<&str> {
            match self {
                Self::Single { name, .. } => name.as_deref(),
                Self::Multiple { name, .. } => name.as_deref(),
            }
        }
    }

    #[derive(Debug, serde::Deserialize, PartialEq)]
    pub struct Instance {
        #[serde(rename = "CLASSNAME")]
        pub class_name: String,
        #[serde(rename = "$value")]
        pub properties: Vec<Property>,
    }

    #[derive(Debug, serde::Deserialize, PartialEq)]
    pub struct NamedInstance {
        #[serde(rename = "INSTANCE")]
        pub instance: Instance,
    }

    #[derive(Debug, serde::Deserialize, PartialEq)]
    pub struct IReturnValue {
        #[serde(rename = "VALUE.NAMEDINSTANCE")]
        pub named_instance: Vec<NamedInstance>,
    }

    #[derive(Debug, serde::Deserialize, PartialEq)]
    pub struct IMethodResponse {
        #[serde(rename = "IRETURNVALUE")]
        pub i_return_value: IReturnValue,
    }

    #[derive(Debug, serde::Deserialize, PartialEq)]
    pub struct SimpleRsp {
        #[serde(rename = "IMETHODRESPONSE")]
        pub imethodresponse: IMethodResponse,
    }

    #[derive(Debug, serde::Deserialize, PartialEq)]
    pub struct Message {
        #[serde(rename = "SIMPLERSP")]
        pub simplersp: SimpleRsp,
    }

    #[derive(Debug, serde::Deserialize, PartialEq)]
    pub struct Cim {
        #[serde(rename = "MESSAGE")]
        pub message: Message,
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[test]
        fn test_instance_list() {
            let xml = include_bytes!("../fixtures/instance_list.xml");

            let r: Cim = quick_xml::de::from_str(std::str::from_utf8(xml).unwrap()).unwrap();

            insta::assert_debug_snapshot!(r);
        }
    }
}
