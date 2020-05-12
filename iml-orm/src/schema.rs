#[derive(SqlType)]
#[postgres(type_name = "lustre_fid")]
pub struct SqlLustreFid;

table! {
    auth_group (id) {
        id -> Int4,
        name -> Varchar,
    }
}

table! {
    auth_group_permissions (id) {
        id -> Int4,
        group_id -> Int4,
        permission_id -> Int4,
    }
}

table! {
    auth_permission (id) {
        id -> Int4,
        name -> Varchar,
        content_type_id -> Int4,
        codename -> Varchar,
    }
}

table! {
    auth_user (id) {
        id -> Int4,
        password -> Varchar,
        last_login -> Nullable<Timestamptz>,
        is_superuser -> Bool,
        username -> Varchar,
        first_name -> Varchar,
        last_name -> Varchar,
        email -> Varchar,
        is_staff -> Bool,
        is_active -> Bool,
        date_joined -> Timestamptz,
    }
}

table! {
    auth_user_groups (id) {
        id -> Int4,
        user_id -> Int4,
        group_id -> Int4,
    }
}

table! {
    auth_user_user_permissions (id) {
        id -> Int4,
        user_id -> Int4,
        permission_id -> Int4,
    }
}

table! {
    chroma_core_addostpooljob (job_ptr_id) {
        job_ptr_id -> Int4,
        ost_id -> Int4,
        pool_id -> Int4,
    }
}

table! {
    chroma_core_aggregatestratagemresultsjob (job_ptr_id) {
        job_ptr_id -> Int4,
        fs_name -> Varchar,
    }
}

table! {
    chroma_core_alertemail (id) {
        id -> Int4,
    }
}

table! {
    chroma_core_alertemail_alerts (id) {
        id -> Int4,
        alertemail_id -> Int4,
        alertstate_id -> Int4,
    }
}

table! {
    chroma_core_alertstate (id) {
        id -> Int4,
        record_type -> Varchar,
        variant -> Varchar,
        alert_item_id -> Nullable<Int4>,
        alert_type -> Varchar,
        begin -> Timestamptz,
        end -> Nullable<Timestamptz>,
        message -> Nullable<Text>,
        active -> Nullable<Bool>,
        dismissed -> Bool,
        severity -> Int4,
        lustre_pid -> Nullable<Int4>,
        alert_item_type_id -> Nullable<Int4>,
    }
}

table! {
    chroma_core_alertsubscription (id) {
        id -> Int4,
        alert_type_id -> Int4,
        user_id -> Int4,
    }
}

table! {
    chroma_core_applyconfparams (job_ptr_id) {
        job_ptr_id -> Int4,
        mgs_id -> Int4,
    }
}

table! {
    chroma_core_autoconfigurecorosync2job (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        corosync_configuration_id -> Int4,
    }
}

table! {
    chroma_core_autoconfigurecorosyncjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        corosync_configuration_id -> Int4,
    }
}

table! {
    chroma_core_clearoldstratagemdatajob (job_ptr_id) {
        job_ptr_id -> Int4,
    }
}

table! {
    chroma_core_clientcertificate (id) {
        id -> Int4,
        serial -> Varchar,
        revoked -> Bool,
        host_id -> Int4,
    }
}

table! {
    chroma_core_command (id) {
        id -> Int4,
        complete -> Bool,
        errored -> Bool,
        cancelled -> Bool,
        message -> Varchar,
        created_at -> Timestamptz,
    }
}

table! {
    chroma_core_command_jobs (id) {
        id -> Int4,
        command_id -> Int4,
        job_id -> Int4,
    }
}

table! {
    chroma_core_configurecopytooljob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        copytool_id -> Int4,
    }
}

table! {
    chroma_core_configurecorosync2job (job_ptr_id) {
        job_ptr_id -> Int4,
        mcast_port -> Nullable<Int4>,
        corosync_configuration_id -> Int4,
        network_interface_0_id -> Int4,
        network_interface_1_id -> Int4,
    }
}

table! {
    chroma_core_configurecorosyncjob (job_ptr_id) {
        job_ptr_id -> Int4,
        mcast_port -> Nullable<Int4>,
        corosync_configuration_id -> Int4,
        network_interface_0_id -> Int4,
        network_interface_1_id -> Int4,
    }
}

table! {
    chroma_core_configurehostfencingjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_configurelnetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        config_changes -> Varchar,
        lnet_configuration_id -> Int4,
    }
}

table! {
    chroma_core_configurentpjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        ntp_configuration_id -> Int4,
    }
}

table! {
    chroma_core_configurepacemakerjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        pacemaker_configuration_id -> Int4,
    }
}

table! {
    chroma_core_configurestratagemjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        stratagem_configuration_id -> Int4,
    }
}

table! {
    chroma_core_configuretargetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_id -> Int4,
    }
}

table! {
    chroma_core_confparam (id) {
        id -> Int4,
        key -> Varchar,
        value -> Nullable<Varchar>,
        version -> Int4,
        content_type_id -> Nullable<Int4>,
        mgs_id -> Int4,
    }
}

table! {
    chroma_core_copytool (id) {
        id -> Int4,
        state_modified_at -> Timestamptz,
        state -> Varchar,
        immutable_state -> Bool,
        index -> Int4,
        bin_path -> Varchar,
        archive -> Int4,
        mountpoint -> Varchar,
        hsm_arguments -> Varchar,
        uuid -> Nullable<Varchar>,
        pid -> Nullable<Int4>,
        not_deleted -> Nullable<Bool>,
        client_mount_id -> Nullable<Int4>,
        content_type_id -> Nullable<Int4>,
        filesystem_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_copytooloperation (id) {
        id -> Int4,
        state -> Int2,
        #[sql_name = "type"]
        type_ -> Int2,
        started_at -> Nullable<Timestamptz>,
        updated_at -> Nullable<Timestamptz>,
        finished_at -> Nullable<Timestamptz>,
        processed_bytes -> Nullable<Int8>,
        total_bytes -> Nullable<Int8>,
        path -> Nullable<Varchar>,
        fid -> Nullable<Varchar>,
        info -> Nullable<Varchar>,
        copytool_id -> Int4,
    }
}

table! {
    chroma_core_corosync2configuration (corosyncconfiguration_ptr_id) {
        corosyncconfiguration_ptr_id -> Int4,
    }
}

table! {
    chroma_core_corosyncconfiguration (id) {
        id -> Int4,
        state_modified_at -> Timestamptz,
        state -> Varchar,
        immutable_state -> Bool,
        not_deleted -> Nullable<Bool>,
        mcast_port -> Nullable<Int4>,
        corosync_reported_up -> Bool,
        record_type -> Varchar,
        content_type_id -> Nullable<Int4>,
        host_id -> Int4,
    }
}

table! {
    chroma_core_createostpooljob (job_ptr_id) {
        job_ptr_id -> Int4,
        pool_id -> Int4,
    }
}

table! {
    chroma_core_createtaskjob (job_ptr_id) {
        job_ptr_id -> Int4,
        task_id -> Int4,
    }
}

table! {
    chroma_core_deployhostjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        managed_host_id -> Int4,
    }
}

table! {
    chroma_core_destroyostpooljob (job_ptr_id) {
        job_ptr_id -> Int4,
        pool_id -> Int4,
    }
}

table! {
    chroma_core_detecttargetsjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_ids -> Varchar,
    }
}

table! {
    chroma_core_device (id) {
        id -> Int4,
        fqdn -> Varchar,
        devices -> Jsonb,
    }
}

table! {
    chroma_core_enablelnetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_object_id -> Int4,
    }
}

table! {
    chroma_core_failbacktargetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        target_id -> Int4,
    }
}

table! {
    chroma_core_failovertargetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        target_id -> Int4,
    }
}

table! {
    use diesel::sql_types::*;
    use super::SqlLustreFid;

    chroma_core_fidtaskqueue (id) {
        id -> Int4,
        fid -> SqlLustreFid,
        data -> Jsonb,
        errno -> Int2,
        task_id -> Int4,
    }
}

table! {
    chroma_core_filesystemclientconfparam (confparam_ptr_id) {
        confparam_ptr_id -> Int4,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_filesystemglobalconfparam (confparam_ptr_id) {
        confparam_ptr_id -> Int4,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_filesystemticket (ticket_ptr_id) {
        ticket_ptr_id -> Int4,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_forceremovecopytooljob (job_ptr_id) {
        job_ptr_id -> Int4,
        copytool_id -> Int4,
    }
}

table! {
    chroma_core_forceremovehostjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_forgetfilesystemjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_forgetstratagemconfigurationjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        stratagem_configuration_id -> Int4,
    }
}

table! {
    chroma_core_forgettargetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_id -> Int4,
    }
}

table! {
    chroma_core_forgetticketjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        ticket_id -> Int4,
    }
}

table! {
    chroma_core_formattargetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_id -> Int4,
    }
}

table! {
    chroma_core_getcorosyncstatejob (job_ptr_id) {
        job_ptr_id -> Int4,
        corosync_configuration_id -> Int4,
    }
}

table! {
    chroma_core_getlnetstatejob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_getpacemakerstatejob (job_ptr_id) {
        job_ptr_id -> Int4,
        pacemaker_configuration_id -> Int4,
    }
}

table! {
    chroma_core_grantrevokedticketjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        ticket_id -> Int4,
    }
}

table! {
    chroma_core_installhostpackagesjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        managed_host_id -> Int4,
    }
}

table! {
    chroma_core_job (id) {
        id -> Int4,
        state -> Varchar,
        errored -> Bool,
        cancelled -> Bool,
        modified_at -> Timestamptz,
        created_at -> Timestamptz,
        wait_for_json -> Text,
        locks_json -> Text,
        content_type_id -> Nullable<Int4>,
    }
}

table! {
    chroma_core_lnetconfiguration (id) {
        id -> Int4,
        state_modified_at -> Timestamptz,
        state -> Varchar,
        immutable_state -> Bool,
        not_deleted -> Nullable<Bool>,
        content_type_id -> Nullable<Int4>,
        host_id -> Int4,
    }
}

table! {
    chroma_core_loadlnetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        lnet_configuration_id -> Int4,
    }
}

table! {
    chroma_core_logmessage (id) {
        id -> Int4,
        datetime -> Timestamptz,
        fqdn -> Varchar,
        severity -> Int2,
        facility -> Int2,
        tag -> Varchar,
        message -> Text,
        message_class -> Int2,
    }
}

table! {
    chroma_core_lustreclientmount (id) {
        id -> Int4,
        state_modified_at -> Timestamptz,
        state -> Varchar,
        immutable_state -> Bool,
        not_deleted -> Nullable<Bool>,
        mountpoint -> Nullable<Varchar>,
        content_type_id -> Nullable<Int4>,
        filesystem_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_makeavailablefilesystemunavailable (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_managedfilesystem (id) {
        id -> Int4,
        state_modified_at -> Timestamptz,
        state -> Varchar,
        immutable_state -> Bool,
        name -> Varchar,
        mdt_next_index -> Int4,
        ost_next_index -> Int4,
        not_deleted -> Nullable<Bool>,
        content_type_id -> Nullable<Int4>,
        mgs_id -> Int4,
    }
}

table! {
    chroma_core_managedhost (id) {
        id -> Int4,
        state_modified_at -> Timestamptz,
        state -> Varchar,
        immutable_state -> Bool,
        not_deleted -> Nullable<Bool>,
        address -> Varchar,
        fqdn -> Varchar,
        nodename -> Varchar,
        boot_time -> Nullable<Timestamptz>,
        needs_update -> Bool,
        corosync_ring0 -> Varchar,
        install_method -> Varchar,
        properties -> Text,
        content_type_id -> Nullable<Int4>,
        server_profile_id -> Nullable<Varchar>,
    }
}

table! {
    chroma_core_managedhost_ha_cluster_peers (id) {
        id -> Int4,
        from_managedhost_id -> Int4,
        to_managedhost_id -> Int4,
    }
}

table! {
    chroma_core_managedmdt (managedtarget_ptr_id) {
        managedtarget_ptr_id -> Int4,
        index -> Int4,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_managedmgs (managedtarget_ptr_id) {
        managedtarget_ptr_id -> Int4,
        conf_param_version -> Int4,
        conf_param_version_applied -> Int4,
    }
}

table! {
    chroma_core_managedost (managedtarget_ptr_id) {
        managedtarget_ptr_id -> Int4,
        index -> Int4,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_managedtarget (id) {
        id -> Int4,
        state_modified_at -> Timestamptz,
        state -> Varchar,
        immutable_state -> Bool,
        name -> Nullable<Varchar>,
        uuid -> Nullable<Varchar>,
        ha_label -> Nullable<Varchar>,
        inode_size -> Nullable<Int4>,
        bytes_per_inode -> Nullable<Int4>,
        inode_count -> Nullable<Int8>,
        reformat -> Bool,
        not_deleted -> Nullable<Bool>,
        active_mount_id -> Nullable<Int4>,
        content_type_id -> Nullable<Int4>,
        volume_id -> Int4,
    }
}

table! {
    chroma_core_managedtargetmount (id) {
        id -> Int4,
        mount_point -> Nullable<Varchar>,
        primary -> Bool,
        not_deleted -> Nullable<Bool>,
        host_id -> Int4,
        target_id -> Int4,
        volume_node_id -> Int4,
    }
}

table! {
    chroma_core_masterticket (ticket_ptr_id) {
        ticket_ptr_id -> Int4,
        mgs_id -> Int4,
    }
}

table! {
    chroma_core_mdtconfparam (confparam_ptr_id) {
        confparam_ptr_id -> Int4,
        mdt_id -> Int4,
    }
}

table! {
    chroma_core_mountlustreclientjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        lustre_client_mount_id -> Int4,
    }
}

table! {
    chroma_core_mountlustrefilesystemsjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_networkinterface (id) {
        id -> Int4,
        name -> Varchar,
        inet4_address -> Varchar,
        inet4_prefix -> Int4,
        #[sql_name = "type"]
        type_ -> Varchar,
        state_up -> Bool,
        corosync_configuration_id -> Nullable<Int4>,
        host_id -> Int4,
    }
}

table! {
    chroma_core_nid (network_interface_id) {
        network_interface_id -> Int4,
        lnd_network -> Nullable<Int4>,
        lnd_type -> Nullable<Varchar>,
        lnet_configuration_id -> Int4,
    }
}

table! {
    chroma_core_ntpconfiguration (id) {
        id -> Int4,
        state_modified_at -> Timestamptz,
        state -> Varchar,
        immutable_state -> Bool,
        not_deleted -> Nullable<Bool>,
        content_type_id -> Nullable<Int4>,
        host_id -> Int4,
    }
}

table! {
    chroma_core_ostconfparam (confparam_ptr_id) {
        confparam_ptr_id -> Int4,
        ost_id -> Int4,
    }
}

table! {
    chroma_core_ostpool (id) {
        id -> Int4,
        name -> Varchar,
        not_deleted -> Nullable<Bool>,
        content_type_id -> Nullable<Int4>,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_ostpool_osts (id) {
        id -> Int4,
        ostpool_id -> Int4,
        managedost_id -> Int4,
    }
}

table! {
    chroma_core_pacemakerconfiguration (id) {
        id -> Int4,
        state_modified_at -> Timestamptz,
        state -> Varchar,
        immutable_state -> Bool,
        not_deleted -> Nullable<Bool>,
        content_type_id -> Nullable<Int4>,
        host_id -> Int4,
    }
}

table! {
    chroma_core_powercontroldevice (id) {
        id -> Int4,
        not_deleted -> Nullable<Bool>,
        name -> Varchar,
        address -> Inet,
        port -> Int4,
        username -> Varchar,
        password -> Varchar,
        options -> Nullable<Varchar>,
        device_type_id -> Int4,
    }
}

table! {
    chroma_core_powercontroldeviceoutlet (id) {
        id -> Int4,
        not_deleted -> Nullable<Bool>,
        identifier -> Varchar,
        has_power -> Nullable<Bool>,
        device_id -> Int4,
        host_id -> Nullable<Int4>,
    }
}

table! {
    chroma_core_powercontroltype (id) {
        id -> Int4,
        not_deleted -> Nullable<Bool>,
        agent -> Varchar,
        make -> Nullable<Varchar>,
        model -> Nullable<Varchar>,
        max_outlets -> Int4,
        default_port -> Int4,
        default_username -> Nullable<Varchar>,
        default_password -> Nullable<Varchar>,
        default_options -> Varchar,
        poweron_template -> Varchar,
        powercycle_template -> Varchar,
        poweroff_template -> Varchar,
        monitor_template -> Varchar,
        outlet_query_template -> Varchar,
        outlet_list_template -> Nullable<Varchar>,
    }
}

table! {
    chroma_core_powercyclehostjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_poweroffhostjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_poweronhostjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_reboothostjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_registertargetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_id -> Int4,
    }
}

table! {
    chroma_core_registrationtoken (id) {
        id -> Int4,
        expiry -> Timestamptz,
        cancelled -> Bool,
        secret -> Varchar,
        credits -> Int4,
        profile_id -> Nullable<Varchar>,
    }
}

table! {
    chroma_core_removeconfiguredtargetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_id -> Int4,
    }
}

table! {
    chroma_core_removecopytooljob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        copytool_id -> Int4,
    }
}

table! {
    chroma_core_removefilesystemjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_removehostjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        host_id -> Int4,
    }
}

table! {
    chroma_core_removelustreclientjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        lustre_client_mount_id -> Int4,
    }
}

table! {
    chroma_core_removemanagedhostjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        host_id -> Int4,
    }
}

table! {
    chroma_core_removeostpooljob (job_ptr_id) {
        job_ptr_id -> Int4,
        ost_id -> Int4,
        pool_id -> Int4,
    }
}

table! {
    chroma_core_removestratagemjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        stratagem_configuration_id -> Int4,
    }
}

table! {
    chroma_core_removetargetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_id -> Int4,
    }
}

table! {
    chroma_core_removetaskjob (job_ptr_id) {
        job_ptr_id -> Int4,
        task_id -> Int4,
    }
}

table! {
    chroma_core_removeunconfiguredcopytooljob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        copytool_id -> Int4,
    }
}

table! {
    chroma_core_removeunconfiguredhostjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        host_id -> Int4,
    }
}

table! {
    chroma_core_repo (repo_name) {
        repo_name -> Varchar,
        location -> Varchar,
    }
}

table! {
    chroma_core_revokegrantedticketjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        ticket_id -> Int4,
    }
}

table! {
    chroma_core_runstratagemjob (job_ptr_id) {
        job_ptr_id -> Int4,
        mdt_id -> Int4,
        uuid -> Varchar,
        report_duration -> Nullable<Int8>,
        purge_duration -> Nullable<Int8>,
        fqdn -> Varchar,
        target_name -> Varchar,
        filesystem_type -> Varchar,
        target_mount_point -> Varchar,
        device_path -> Varchar,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_sendstratagemresultstoclientjob (job_ptr_id) {
        job_ptr_id -> Int4,
        uuid -> Varchar,
        report_duration -> Nullable<Int8>,
        purge_duration -> Nullable<Int8>,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_serverprofile (name) {
        name -> Varchar,
        ui_name -> Varchar,
        ui_description -> Text,
        managed -> Bool,
        worker -> Bool,
        user_selectable -> Bool,
        initial_state -> Varchar,
        ntp -> Bool,
        corosync -> Bool,
        corosync2 -> Bool,
        pacemaker -> Bool,
        default -> Bool,
    }
}

table! {
    chroma_core_serverprofilepackage (id) {
        id -> Int4,
        package_name -> Varchar,
        server_profile_id -> Varchar,
    }
}

table! {
    chroma_core_serverprofile_repolist (id) {
        id -> Int4,
        serverprofile_id -> Varchar,
        repo_id -> Varchar,
    }
}

table! {
    chroma_core_serverprofilevalidation (id) {
        id -> Int4,
        test -> Varchar,
        description -> Varchar,
        server_profile_id -> Varchar,
    }
}

table! {
    chroma_core_sethostprofilejob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
        server_profile_id -> Varchar,
    }
}

table! {
    chroma_core_setuphostjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_object_id -> Int4,
    }
}

table! {
    chroma_core_setupmonitoredhostjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_object_id -> Int4,
    }
}

table! {
    chroma_core_setupworkerjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_object_id -> Int4,
    }
}

table! {
    chroma_core_shutdownhostjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_startcopytooljob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        copytool_id -> Int4,
    }
}

table! {
    chroma_core_startcorosync2job (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        corosync_configuration_id -> Int4,
    }
}

table! {
    chroma_core_startcorosyncjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        corosync_configuration_id -> Int4,
    }
}

table! {
    chroma_core_startlnetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        lnet_configuration_id -> Int4,
    }
}

table! {
    chroma_core_startpacemakerjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        pacemaker_configuration_id -> Int4,
    }
}

table! {
    chroma_core_startstoppedfilesystemjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_starttargetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_id -> Int4,
    }
}

table! {
    chroma_core_startunavailablefilesystemjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_stepresult (id) {
        id -> Int4,
        step_klass -> Text,
        args -> Text,
        step_index -> Int4,
        step_count -> Int4,
        log -> Text,
        console -> Text,
        backtrace -> Text,
        state -> Varchar,
        modified_at -> Timestamptz,
        created_at -> Timestamptz,
        result -> Nullable<Text>,
        job_id -> Int4,
    }
}

table! {
    chroma_core_stopcopytooljob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        copytool_id -> Int4,
    }
}

table! {
    chroma_core_stopcorosync2job (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        corosync_configuration_id -> Int4,
    }
}

table! {
    chroma_core_stopcorosyncjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        corosync_configuration_id -> Int4,
    }
}

table! {
    chroma_core_stoplnetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        lnet_configuration_id -> Int4,
    }
}

table! {
    chroma_core_stoppacemakerjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        pacemaker_configuration_id -> Int4,
    }
}

table! {
    chroma_core_stoptargetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_id -> Int4,
    }
}

table! {
    chroma_core_stopunavailablefilesystemjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_storagealertpropagated (id) {
        id -> Int4,
        storage_resource_id -> Int4,
        alert_state_id -> Int4,
    }
}

table! {
    chroma_core_storagepluginrecord (id) {
        id -> Int4,
        module_name -> Varchar,
        internal -> Bool,
    }
}

table! {
    chroma_core_storageresourceattributereference (id) {
        id -> Int4,
        key -> Varchar,
        resource_id -> Int4,
        value_id -> Nullable<Int4>,
    }
}

table! {
    chroma_core_storageresourceattributeserialized (id) {
        id -> Int4,
        key -> Varchar,
        value -> Text,
        resource_id -> Int4,
    }
}

table! {
    chroma_core_storageresourceclass (id) {
        id -> Int4,
        class_name -> Varchar,
        user_creatable -> Bool,
        storage_plugin_id -> Int4,
    }
}

table! {
    chroma_core_storageresourcerecord (id) {
        id -> Int4,
        storage_id_str -> Varchar,
        alias -> Nullable<Varchar>,
        resource_class_id -> Int4,
        storage_id_scope_id -> Nullable<Int4>,
    }
}

table! {
    chroma_core_storageresourcerecord_parents (id) {
        id -> Int4,
        from_storageresourcerecord_id -> Int4,
        to_storageresourcerecord_id -> Int4,
    }
}

table! {
    chroma_core_storageresourcerecord_reported_by (id) {
        id -> Int4,
        from_storageresourcerecord_id -> Int4,
        to_storageresourcerecord_id -> Int4,
    }
}

table! {
    chroma_core_stratagemconfiguration (id) {
        id -> Int4,
        state_modified_at -> Timestamptz,
        state -> Varchar,
        immutable_state -> Bool,
        interval -> Int8,
        report_duration -> Nullable<Int8>,
        purge_duration -> Nullable<Int8>,
        not_deleted -> Nullable<Bool>,
        filesystem_id -> Int4,
    }
}

table! {
    chroma_core_targetrecoveryinfo (id) {
        id -> Int4,
        recovery_status -> Text,
        target_id -> Int4,
    }
}

table! {
    chroma_core_task (id) {
        id -> Int4,
        name -> Varchar,
        start -> Timestamptz,
        finish -> Nullable<Timestamptz>,
        state -> Varchar,
        fids_total -> Int8,
        fids_completed -> Int8,
        fids_failed -> Int8,
        data_transfered -> Int8,
        single_runner -> Bool,
        keep_failed -> Bool,
        actions -> Array<Text>,
        args -> Jsonb,
        filesystem_id -> Int4,
        running_on_id -> Nullable<Int4>,
    }
}

table! {
    chroma_core_testhostconnectionjob (job_ptr_id) {
        job_ptr_id -> Int4,
        address -> Varchar,
        credentials_key -> Int4,
    }
}

table! {
    chroma_core_ticket (id) {
        id -> Int4,
        state_modified_at -> Timestamptz,
        state -> Varchar,
        immutable_state -> Bool,
        ha_label -> Nullable<Varchar>,
        name -> Varchar,
        resource_controlled -> Bool,
        not_deleted -> Nullable<Bool>,
        content_type_id -> Nullable<Int4>,
    }
}

table! {
    chroma_core_triggerpluginupdatesjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_ids -> Varchar,
        plugin_names_json -> Varchar,
    }
}

table! {
    chroma_core_unconfigurecorosync2job (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        corosync_configuration_id -> Int4,
    }
}

table! {
    chroma_core_unconfigurecorosyncjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        corosync_configuration_id -> Int4,
    }
}

table! {
    chroma_core_unconfigurelnetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        target_object_id -> Int4,
    }
}

table! {
    chroma_core_unconfigurentpjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        ntp_configuration_id -> Int4,
    }
}

table! {
    chroma_core_unconfigurepacemakerjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        pacemaker_configuration_id -> Int4,
    }
}

table! {
    chroma_core_unconfigurestratagemjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        stratagem_configuration_id -> Int4,
    }
}

table! {
    chroma_core_unloadlnetjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        lnet_configuration_id -> Int4,
    }
}

table! {
    chroma_core_unmountlustreclientmountjob (job_ptr_id) {
        job_ptr_id -> Int4,
        old_state -> Varchar,
        lustre_client_mount_id -> Int4,
    }
}

table! {
    chroma_core_unmountlustrefilesystemsjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_updatedevicesjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_ids -> Varchar,
    }
}

table! {
    chroma_core_updatejob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_updatenidsjob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_ids -> Varchar,
    }
}

table! {
    chroma_core_updateyumfilejob (job_ptr_id) {
        job_ptr_id -> Int4,
        host_id -> Int4,
    }
}

table! {
    chroma_core_volume (id) {
        id -> Int4,
        size -> Nullable<Int8>,
        label -> Varchar,
        filesystem_type -> Nullable<Varchar>,
        usable_for_lustre -> Bool,
        not_deleted -> Nullable<Bool>,
        storage_resource_id -> Nullable<Int4>,
    }
}

table! {
    chroma_core_volumenode (id) {
        id -> Int4,
        path -> Varchar,
        primary -> Bool,
        #[sql_name = "use"]
        use_ -> Bool,
        not_deleted -> Nullable<Bool>,
        host_id -> Int4,
        storage_resource_id -> Nullable<Int4>,
        volume_id -> Int4,
    }
}

table! {
    django_content_type (id) {
        id -> Int4,
        app_label -> Varchar,
        model -> Varchar,
    }
}

table! {
    django_migrations (id) {
        id -> Int4,
        app -> Varchar,
        name -> Varchar,
        applied -> Timestamptz,
    }
}

table! {
    django_session (session_key) {
        session_key -> Varchar,
        session_data -> Text,
        expire_date -> Timestamptz,
    }
}

table! {
    django_site (id) {
        id -> Int4,
        domain -> Varchar,
        name -> Varchar,
    }
}

table! {
    tastypie_apiaccess (id) {
        id -> Int4,
        identifier -> Varchar,
        url -> Text,
        request_method -> Varchar,
        accessed -> Int4,
    }
}

table! {
    tastypie_apikey (id) {
        id -> Int4,
        key -> Varchar,
        created -> Timestamptz,
        user_id -> Int4,
    }
}

joinable!(auth_group_permissions -> auth_group (group_id));
joinable!(auth_group_permissions -> auth_permission (permission_id));
joinable!(auth_permission -> django_content_type (content_type_id));
joinable!(auth_user_groups -> auth_group (group_id));
joinable!(auth_user_groups -> auth_user (user_id));
joinable!(auth_user_user_permissions -> auth_permission (permission_id));
joinable!(auth_user_user_permissions -> auth_user (user_id));
joinable!(chroma_core_addostpooljob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_addostpooljob -> chroma_core_managedost (ost_id));
joinable!(chroma_core_addostpooljob -> chroma_core_ostpool (pool_id));
joinable!(chroma_core_aggregatestratagemresultsjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_alertemail_alerts -> chroma_core_alertemail (alertemail_id));
joinable!(chroma_core_alertemail_alerts -> chroma_core_alertstate (alertstate_id));
joinable!(chroma_core_alertstate -> django_content_type (alert_item_type_id));
joinable!(chroma_core_alertsubscription -> auth_user (user_id));
joinable!(chroma_core_alertsubscription -> django_content_type (alert_type_id));
joinable!(chroma_core_applyconfparams -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_applyconfparams -> chroma_core_managedtarget (mgs_id));
joinable!(chroma_core_autoconfigurecorosync2job -> chroma_core_corosync2configuration (corosync_configuration_id));
joinable!(chroma_core_autoconfigurecorosync2job -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_autoconfigurecorosyncjob -> chroma_core_corosyncconfiguration (corosync_configuration_id));
joinable!(chroma_core_autoconfigurecorosyncjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_clearoldstratagemdatajob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_clientcertificate -> chroma_core_managedhost (host_id));
joinable!(chroma_core_command_jobs -> chroma_core_command (command_id));
joinable!(chroma_core_command_jobs -> chroma_core_job (job_id));
joinable!(chroma_core_configurecopytooljob -> chroma_core_copytool (copytool_id));
joinable!(chroma_core_configurecopytooljob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_configurecorosync2job -> chroma_core_corosync2configuration (corosync_configuration_id));
joinable!(chroma_core_configurecorosync2job -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_configurecorosyncjob -> chroma_core_corosyncconfiguration (corosync_configuration_id));
joinable!(chroma_core_configurecorosyncjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_configurehostfencingjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_configurehostfencingjob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_configurelnetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_configurelnetjob -> chroma_core_lnetconfiguration (lnet_configuration_id));
joinable!(chroma_core_configurentpjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_configurentpjob -> chroma_core_ntpconfiguration (ntp_configuration_id));
joinable!(chroma_core_configurepacemakerjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_configurepacemakerjob -> chroma_core_pacemakerconfiguration (pacemaker_configuration_id));
joinable!(chroma_core_configurestratagemjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_configurestratagemjob -> chroma_core_stratagemconfiguration (stratagem_configuration_id));
joinable!(chroma_core_configuretargetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_configuretargetjob -> chroma_core_managedtarget (target_id));
joinable!(chroma_core_confparam -> chroma_core_managedmgs (mgs_id));
joinable!(chroma_core_confparam -> django_content_type (content_type_id));
joinable!(chroma_core_copytool -> chroma_core_lustreclientmount (client_mount_id));
joinable!(chroma_core_copytool -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_copytool -> chroma_core_managedhost (host_id));
joinable!(chroma_core_copytool -> django_content_type (content_type_id));
joinable!(chroma_core_copytooloperation -> chroma_core_copytool (copytool_id));
joinable!(chroma_core_corosync2configuration -> chroma_core_corosyncconfiguration (corosyncconfiguration_ptr_id));
joinable!(chroma_core_corosyncconfiguration -> chroma_core_managedhost (host_id));
joinable!(chroma_core_corosyncconfiguration -> django_content_type (content_type_id));
joinable!(chroma_core_createostpooljob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_createostpooljob -> chroma_core_ostpool (pool_id));
joinable!(chroma_core_createtaskjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_createtaskjob -> chroma_core_task (task_id));
joinable!(chroma_core_deployhostjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_deployhostjob -> chroma_core_managedhost (managed_host_id));
joinable!(chroma_core_destroyostpooljob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_destroyostpooljob -> chroma_core_ostpool (pool_id));
joinable!(chroma_core_detecttargetsjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_enablelnetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_enablelnetjob -> chroma_core_lnetconfiguration (target_object_id));
joinable!(chroma_core_failbacktargetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_failbacktargetjob -> chroma_core_managedtarget (target_id));
joinable!(chroma_core_failovertargetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_failovertargetjob -> chroma_core_managedtarget (target_id));
joinable!(chroma_core_fidtaskqueue -> chroma_core_task (task_id));
joinable!(chroma_core_filesystemclientconfparam -> chroma_core_confparam (confparam_ptr_id));
joinable!(chroma_core_filesystemclientconfparam -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_filesystemglobalconfparam -> chroma_core_confparam (confparam_ptr_id));
joinable!(chroma_core_filesystemglobalconfparam -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_filesystemticket -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_filesystemticket -> chroma_core_ticket (ticket_ptr_id));
joinable!(chroma_core_forceremovecopytooljob -> chroma_core_copytool (copytool_id));
joinable!(chroma_core_forceremovecopytooljob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_forceremovehostjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_forceremovehostjob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_forgetfilesystemjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_forgetfilesystemjob -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_forgetstratagemconfigurationjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_forgetstratagemconfigurationjob -> chroma_core_stratagemconfiguration (stratagem_configuration_id));
joinable!(chroma_core_forgettargetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_forgettargetjob -> chroma_core_managedtarget (target_id));
joinable!(chroma_core_forgetticketjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_forgetticketjob -> chroma_core_ticket (ticket_id));
joinable!(chroma_core_formattargetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_formattargetjob -> chroma_core_managedtarget (target_id));
joinable!(chroma_core_getcorosyncstatejob -> chroma_core_corosyncconfiguration (corosync_configuration_id));
joinable!(chroma_core_getcorosyncstatejob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_getlnetstatejob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_getlnetstatejob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_getpacemakerstatejob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_getpacemakerstatejob -> chroma_core_pacemakerconfiguration (pacemaker_configuration_id));
joinable!(chroma_core_grantrevokedticketjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_grantrevokedticketjob -> chroma_core_ticket (ticket_id));
joinable!(chroma_core_installhostpackagesjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_installhostpackagesjob -> chroma_core_managedhost (managed_host_id));
joinable!(chroma_core_job -> django_content_type (content_type_id));
joinable!(chroma_core_lnetconfiguration -> chroma_core_managedhost (host_id));
joinable!(chroma_core_lnetconfiguration -> django_content_type (content_type_id));
joinable!(chroma_core_loadlnetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_loadlnetjob -> chroma_core_lnetconfiguration (lnet_configuration_id));
joinable!(chroma_core_lustreclientmount -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_lustreclientmount -> chroma_core_managedhost (host_id));
joinable!(chroma_core_lustreclientmount -> django_content_type (content_type_id));
joinable!(chroma_core_makeavailablefilesystemunavailable -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_makeavailablefilesystemunavailable -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_managedfilesystem -> chroma_core_managedmgs (mgs_id));
joinable!(chroma_core_managedfilesystem -> django_content_type (content_type_id));
joinable!(chroma_core_managedhost -> chroma_core_serverprofile (server_profile_id));
joinable!(chroma_core_managedhost -> django_content_type (content_type_id));
joinable!(chroma_core_managedmdt -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_managedmdt -> chroma_core_managedtarget (managedtarget_ptr_id));
joinable!(chroma_core_managedmgs -> chroma_core_managedtarget (managedtarget_ptr_id));
joinable!(chroma_core_managedost -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_managedost -> chroma_core_managedtarget (managedtarget_ptr_id));
joinable!(chroma_core_managedtarget -> chroma_core_volume (volume_id));
joinable!(chroma_core_managedtarget -> django_content_type (content_type_id));
joinable!(chroma_core_managedtargetmount -> chroma_core_managedhost (host_id));
joinable!(chroma_core_managedtargetmount -> chroma_core_volumenode (volume_node_id));
joinable!(chroma_core_masterticket -> chroma_core_managedmgs (mgs_id));
joinable!(chroma_core_masterticket -> chroma_core_ticket (ticket_ptr_id));
joinable!(chroma_core_mdtconfparam -> chroma_core_confparam (confparam_ptr_id));
joinable!(chroma_core_mdtconfparam -> chroma_core_managedmdt (mdt_id));
joinable!(chroma_core_mountlustreclientjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_mountlustreclientjob -> chroma_core_lustreclientmount (lustre_client_mount_id));
joinable!(chroma_core_mountlustrefilesystemsjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_mountlustrefilesystemsjob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_networkinterface -> chroma_core_corosyncconfiguration (corosync_configuration_id));
joinable!(chroma_core_networkinterface -> chroma_core_managedhost (host_id));
joinable!(chroma_core_nid -> chroma_core_lnetconfiguration (lnet_configuration_id));
joinable!(chroma_core_nid -> chroma_core_networkinterface (network_interface_id));
joinable!(chroma_core_ntpconfiguration -> chroma_core_managedhost (host_id));
joinable!(chroma_core_ntpconfiguration -> django_content_type (content_type_id));
joinable!(chroma_core_ostconfparam -> chroma_core_confparam (confparam_ptr_id));
joinable!(chroma_core_ostconfparam -> chroma_core_managedost (ost_id));
joinable!(chroma_core_ostpool -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_ostpool -> django_content_type (content_type_id));
joinable!(chroma_core_ostpool_osts -> chroma_core_managedost (managedost_id));
joinable!(chroma_core_ostpool_osts -> chroma_core_ostpool (ostpool_id));
joinable!(chroma_core_pacemakerconfiguration -> chroma_core_managedhost (host_id));
joinable!(chroma_core_pacemakerconfiguration -> django_content_type (content_type_id));
joinable!(chroma_core_powercontroldevice -> chroma_core_powercontroltype (device_type_id));
joinable!(chroma_core_powercontroldeviceoutlet -> chroma_core_managedhost (host_id));
joinable!(chroma_core_powercontroldeviceoutlet -> chroma_core_powercontroldevice (device_id));
joinable!(chroma_core_powercyclehostjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_powercyclehostjob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_poweroffhostjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_poweroffhostjob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_poweronhostjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_poweronhostjob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_reboothostjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_reboothostjob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_registertargetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_registertargetjob -> chroma_core_managedtarget (target_id));
joinable!(chroma_core_registrationtoken -> chroma_core_serverprofile (profile_id));
joinable!(chroma_core_removeconfiguredtargetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_removeconfiguredtargetjob -> chroma_core_managedtarget (target_id));
joinable!(chroma_core_removecopytooljob -> chroma_core_copytool (copytool_id));
joinable!(chroma_core_removecopytooljob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_removefilesystemjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_removefilesystemjob -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_removehostjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_removehostjob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_removelustreclientjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_removelustreclientjob -> chroma_core_lustreclientmount (lustre_client_mount_id));
joinable!(chroma_core_removemanagedhostjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_removemanagedhostjob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_removeostpooljob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_removeostpooljob -> chroma_core_managedost (ost_id));
joinable!(chroma_core_removeostpooljob -> chroma_core_ostpool (pool_id));
joinable!(chroma_core_removestratagemjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_removestratagemjob -> chroma_core_stratagemconfiguration (stratagem_configuration_id));
joinable!(chroma_core_removetargetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_removetargetjob -> chroma_core_managedtarget (target_id));
joinable!(chroma_core_removetaskjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_removetaskjob -> chroma_core_task (task_id));
joinable!(chroma_core_removeunconfiguredcopytooljob -> chroma_core_copytool (copytool_id));
joinable!(chroma_core_removeunconfiguredcopytooljob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_removeunconfiguredhostjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_removeunconfiguredhostjob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_revokegrantedticketjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_revokegrantedticketjob -> chroma_core_ticket (ticket_id));
joinable!(chroma_core_runstratagemjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_runstratagemjob -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_sendstratagemresultstoclientjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_sendstratagemresultstoclientjob -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_serverprofile_repolist -> chroma_core_repo (repo_id));
joinable!(chroma_core_serverprofile_repolist -> chroma_core_serverprofile (serverprofile_id));
joinable!(chroma_core_serverprofilepackage -> chroma_core_serverprofile (server_profile_id));
joinable!(chroma_core_serverprofilevalidation -> chroma_core_serverprofile (server_profile_id));
joinable!(chroma_core_sethostprofilejob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_sethostprofilejob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_sethostprofilejob -> chroma_core_serverprofile (server_profile_id));
joinable!(chroma_core_setuphostjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_setuphostjob -> chroma_core_managedhost (target_object_id));
joinable!(chroma_core_setupmonitoredhostjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_setupmonitoredhostjob -> chroma_core_managedhost (target_object_id));
joinable!(chroma_core_setupworkerjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_setupworkerjob -> chroma_core_managedhost (target_object_id));
joinable!(chroma_core_shutdownhostjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_shutdownhostjob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_startcopytooljob -> chroma_core_copytool (copytool_id));
joinable!(chroma_core_startcopytooljob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_startcorosync2job -> chroma_core_corosync2configuration (corosync_configuration_id));
joinable!(chroma_core_startcorosync2job -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_startcorosyncjob -> chroma_core_corosyncconfiguration (corosync_configuration_id));
joinable!(chroma_core_startcorosyncjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_startlnetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_startlnetjob -> chroma_core_lnetconfiguration (lnet_configuration_id));
joinable!(chroma_core_startpacemakerjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_startpacemakerjob -> chroma_core_pacemakerconfiguration (pacemaker_configuration_id));
joinable!(chroma_core_startstoppedfilesystemjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_startstoppedfilesystemjob -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_starttargetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_starttargetjob -> chroma_core_managedtarget (target_id));
joinable!(chroma_core_startunavailablefilesystemjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_startunavailablefilesystemjob -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_stepresult -> chroma_core_job (job_id));
joinable!(chroma_core_stopcopytooljob -> chroma_core_copytool (copytool_id));
joinable!(chroma_core_stopcopytooljob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_stopcorosync2job -> chroma_core_corosync2configuration (corosync_configuration_id));
joinable!(chroma_core_stopcorosync2job -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_stopcorosyncjob -> chroma_core_corosyncconfiguration (corosync_configuration_id));
joinable!(chroma_core_stopcorosyncjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_stoplnetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_stoplnetjob -> chroma_core_lnetconfiguration (lnet_configuration_id));
joinable!(chroma_core_stoppacemakerjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_stoppacemakerjob -> chroma_core_pacemakerconfiguration (pacemaker_configuration_id));
joinable!(chroma_core_stoptargetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_stoptargetjob -> chroma_core_managedtarget (target_id));
joinable!(chroma_core_stopunavailablefilesystemjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_stopunavailablefilesystemjob -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_storagealertpropagated -> chroma_core_alertstate (alert_state_id));
joinable!(chroma_core_storagealertpropagated -> chroma_core_storageresourcerecord (storage_resource_id));
joinable!(chroma_core_storageresourceattributeserialized -> chroma_core_storageresourcerecord (resource_id));
joinable!(chroma_core_storageresourceclass -> chroma_core_storagepluginrecord (storage_plugin_id));
joinable!(chroma_core_storageresourcerecord -> chroma_core_storageresourceclass (resource_class_id));
joinable!(chroma_core_stratagemconfiguration -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_targetrecoveryinfo -> chroma_core_managedtarget (target_id));
joinable!(chroma_core_task -> chroma_core_managedfilesystem (filesystem_id));
joinable!(chroma_core_task -> chroma_core_managedhost (running_on_id));
joinable!(chroma_core_testhostconnectionjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_ticket -> django_content_type (content_type_id));
joinable!(chroma_core_triggerpluginupdatesjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_unconfigurecorosync2job -> chroma_core_corosync2configuration (corosync_configuration_id));
joinable!(chroma_core_unconfigurecorosync2job -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_unconfigurecorosyncjob -> chroma_core_corosyncconfiguration (corosync_configuration_id));
joinable!(chroma_core_unconfigurecorosyncjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_unconfigurelnetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_unconfigurelnetjob -> chroma_core_lnetconfiguration (target_object_id));
joinable!(chroma_core_unconfigurentpjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_unconfigurentpjob -> chroma_core_ntpconfiguration (ntp_configuration_id));
joinable!(chroma_core_unconfigurepacemakerjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_unconfigurepacemakerjob -> chroma_core_pacemakerconfiguration (pacemaker_configuration_id));
joinable!(chroma_core_unconfigurestratagemjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_unconfigurestratagemjob -> chroma_core_stratagemconfiguration (stratagem_configuration_id));
joinable!(chroma_core_unloadlnetjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_unloadlnetjob -> chroma_core_lnetconfiguration (lnet_configuration_id));
joinable!(chroma_core_unmountlustreclientmountjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_unmountlustreclientmountjob -> chroma_core_lustreclientmount (lustre_client_mount_id));
joinable!(chroma_core_unmountlustrefilesystemsjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_unmountlustrefilesystemsjob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_updatedevicesjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_updatejob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_updatejob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_updatenidsjob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_updateyumfilejob -> chroma_core_job (job_ptr_id));
joinable!(chroma_core_updateyumfilejob -> chroma_core_managedhost (host_id));
joinable!(chroma_core_volume -> chroma_core_storageresourcerecord (storage_resource_id));
joinable!(chroma_core_volumenode -> chroma_core_managedhost (host_id));
joinable!(chroma_core_volumenode -> chroma_core_storageresourcerecord (storage_resource_id));
joinable!(chroma_core_volumenode -> chroma_core_volume (volume_id));
joinable!(tastypie_apikey -> auth_user (user_id));

allow_tables_to_appear_in_same_query!(
    auth_group,
    auth_group_permissions,
    auth_permission,
    auth_user,
    auth_user_groups,
    auth_user_user_permissions,
    chroma_core_addostpooljob,
    chroma_core_aggregatestratagemresultsjob,
    chroma_core_alertemail,
    chroma_core_alertemail_alerts,
    chroma_core_alertstate,
    chroma_core_alertsubscription,
    chroma_core_applyconfparams,
    chroma_core_autoconfigurecorosync2job,
    chroma_core_autoconfigurecorosyncjob,
    chroma_core_clearoldstratagemdatajob,
    chroma_core_clientcertificate,
    chroma_core_command,
    chroma_core_command_jobs,
    chroma_core_configurecopytooljob,
    chroma_core_configurecorosync2job,
    chroma_core_configurecorosyncjob,
    chroma_core_configurehostfencingjob,
    chroma_core_configurelnetjob,
    chroma_core_configurentpjob,
    chroma_core_configurepacemakerjob,
    chroma_core_configurestratagemjob,
    chroma_core_configuretargetjob,
    chroma_core_confparam,
    chroma_core_copytool,
    chroma_core_copytooloperation,
    chroma_core_corosync2configuration,
    chroma_core_corosyncconfiguration,
    chroma_core_createostpooljob,
    chroma_core_createtaskjob,
    chroma_core_deployhostjob,
    chroma_core_destroyostpooljob,
    chroma_core_detecttargetsjob,
    chroma_core_device,
    chroma_core_enablelnetjob,
    chroma_core_failbacktargetjob,
    chroma_core_failovertargetjob,
    chroma_core_fidtaskqueue,
    chroma_core_filesystemclientconfparam,
    chroma_core_filesystemglobalconfparam,
    chroma_core_filesystemticket,
    chroma_core_forceremovecopytooljob,
    chroma_core_forceremovehostjob,
    chroma_core_forgetfilesystemjob,
    chroma_core_forgetstratagemconfigurationjob,
    chroma_core_forgettargetjob,
    chroma_core_forgetticketjob,
    chroma_core_formattargetjob,
    chroma_core_getcorosyncstatejob,
    chroma_core_getlnetstatejob,
    chroma_core_getpacemakerstatejob,
    chroma_core_grantrevokedticketjob,
    chroma_core_installhostpackagesjob,
    chroma_core_job,
    chroma_core_lnetconfiguration,
    chroma_core_loadlnetjob,
    chroma_core_logmessage,
    chroma_core_lustreclientmount,
    chroma_core_makeavailablefilesystemunavailable,
    chroma_core_managedfilesystem,
    chroma_core_managedhost,
    chroma_core_managedhost_ha_cluster_peers,
    chroma_core_managedmdt,
    chroma_core_managedmgs,
    chroma_core_managedost,
    chroma_core_managedtarget,
    chroma_core_managedtargetmount,
    chroma_core_masterticket,
    chroma_core_mdtconfparam,
    chroma_core_mountlustreclientjob,
    chroma_core_mountlustrefilesystemsjob,
    chroma_core_networkinterface,
    chroma_core_nid,
    chroma_core_ntpconfiguration,
    chroma_core_ostconfparam,
    chroma_core_ostpool,
    chroma_core_ostpool_osts,
    chroma_core_pacemakerconfiguration,
    chroma_core_powercontroldevice,
    chroma_core_powercontroldeviceoutlet,
    chroma_core_powercontroltype,
    chroma_core_powercyclehostjob,
    chroma_core_poweroffhostjob,
    chroma_core_poweronhostjob,
    chroma_core_reboothostjob,
    chroma_core_registertargetjob,
    chroma_core_registrationtoken,
    chroma_core_removeconfiguredtargetjob,
    chroma_core_removecopytooljob,
    chroma_core_removefilesystemjob,
    chroma_core_removehostjob,
    chroma_core_removelustreclientjob,
    chroma_core_removemanagedhostjob,
    chroma_core_removeostpooljob,
    chroma_core_removestratagemjob,
    chroma_core_removetargetjob,
    chroma_core_removetaskjob,
    chroma_core_removeunconfiguredcopytooljob,
    chroma_core_removeunconfiguredhostjob,
    chroma_core_repo,
    chroma_core_revokegrantedticketjob,
    chroma_core_runstratagemjob,
    chroma_core_sendstratagemresultstoclientjob,
    chroma_core_serverprofile,
    chroma_core_serverprofilepackage,
    chroma_core_serverprofile_repolist,
    chroma_core_serverprofilevalidation,
    chroma_core_sethostprofilejob,
    chroma_core_setuphostjob,
    chroma_core_setupmonitoredhostjob,
    chroma_core_setupworkerjob,
    chroma_core_shutdownhostjob,
    chroma_core_startcopytooljob,
    chroma_core_startcorosync2job,
    chroma_core_startcorosyncjob,
    chroma_core_startlnetjob,
    chroma_core_startpacemakerjob,
    chroma_core_startstoppedfilesystemjob,
    chroma_core_starttargetjob,
    chroma_core_startunavailablefilesystemjob,
    chroma_core_stepresult,
    chroma_core_stopcopytooljob,
    chroma_core_stopcorosync2job,
    chroma_core_stopcorosyncjob,
    chroma_core_stoplnetjob,
    chroma_core_stoppacemakerjob,
    chroma_core_stoptargetjob,
    chroma_core_stopunavailablefilesystemjob,
    chroma_core_storagealertpropagated,
    chroma_core_storagepluginrecord,
    chroma_core_storageresourceattributereference,
    chroma_core_storageresourceattributeserialized,
    chroma_core_storageresourceclass,
    chroma_core_storageresourcerecord,
    chroma_core_storageresourcerecord_parents,
    chroma_core_storageresourcerecord_reported_by,
    chroma_core_stratagemconfiguration,
    chroma_core_targetrecoveryinfo,
    chroma_core_task,
    chroma_core_testhostconnectionjob,
    chroma_core_ticket,
    chroma_core_triggerpluginupdatesjob,
    chroma_core_unconfigurecorosync2job,
    chroma_core_unconfigurecorosyncjob,
    chroma_core_unconfigurelnetjob,
    chroma_core_unconfigurentpjob,
    chroma_core_unconfigurepacemakerjob,
    chroma_core_unconfigurestratagemjob,
    chroma_core_unloadlnetjob,
    chroma_core_unmountlustreclientmountjob,
    chroma_core_unmountlustrefilesystemsjob,
    chroma_core_updatedevicesjob,
    chroma_core_updatejob,
    chroma_core_updatenidsjob,
    chroma_core_updateyumfilejob,
    chroma_core_volume,
    chroma_core_volumenode,
    django_content_type,
    django_migrations,
    django_session,
    django_site,
    tastypie_apiaccess,
    tastypie_apikey,
);
