CREATE TYPE component AS ENUM (
    'host',
    'filesystem',
    'lnet',
    'target',
    'client_mount',
    'ntp',
    'mgt',
    'ost',
    'mdt',
    'mgt_mdt'
);

CREATE TYPE alert_record_type AS ENUM (
    'AlertState',
    'LearnEvent',
    'AlertEvent',
    'SyslogEvent',
    'ClientConnectEvent',
    'CommandRunningAlert',
    'CommandSuccessfulAlert',
    'CommandCancelledAlert',
    'CommandErroredAlert',
    'CorosyncUnknownPeersAlert',
    'CorosyncToManyPeersAlert',
    'CorosyncNoPeersAlert',
    'CorosyncStoppedAlert',
    'StonithNotEnabledAlert',
    'PacemakerStoppedAlert',
    'HostContactAlert',
    'HostOfflineAlert',
    'HostRebootEvent',
    'TargetOfflineAlert',
    'TargetRecoveryAlert',
    'StorageResourceOffline',
    'StorageResourceAlert',
    'StorageResourceLearnEvent',
    'IpmiBmcUnavailableAlert',
    'LNetOfflineAlert',
    'LNetNidsChangedAlert',
    'StratagemUnconfiguredAlert',
    'TimeOutOfSyncAlert',
    'NoTimeSyncAlert',
    'MultipleTimeSyncAlert',
    'UnknownTimeSyncAlert'
);

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS alertstate (
    id serial PRIMARY KEY,
    alert_item_type_id component,
    alert_item_id integer,
    alert_type character varying(128) NOT NULL,
    "begin" timestamp WITH time zone NOT NULL,
    "end" timestamp WITH time zone,
    active boolean NOT NULL,
    dismissed boolean NOT NULL,
    severity integer NOT NULL,
    record_type alert_record_type NOT NULL,
    variant character varying(512) NOT NULL,
    lustre_pid integer,
    message text,
    CONSTRAINT unique_active_alert EXCLUDE USING gist (
        record_type WITH =,
        alert_item_type_id WITH =,
        alert_item_id WITH =,
        int4(active) WITH =
    )
    WHERE (int4(active) = 1)
);

DROP TRIGGER IF EXISTS alertstate_notify_update ON alertstate;

DROP TRIGGER IF EXISTS alertstate_notify_insert ON alertstate;

DROP TRIGGER IF EXISTS alertstate_notify_delete ON alertstate;

CREATE TRIGGER alertstate_notify_update
AFTER
UPDATE ON alertstate FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER alertstate_notify_insert
AFTER
INSERT ON alertstate FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER alertstate_notify_delete
AFTER DELETE ON alertstate FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

BEGIN;

LOCK TABLE alertstate IN SHARE ROW EXCLUSIVE MODE;

CREATE TRIGGER alertstate_countrows
AFTER
INSERT
    OR DELETE ON alertstate FOR EACH ROW EXECUTE PROCEDURE count_rows();

DELETE FROM rowcount
WHERE table_name = 'alertstate';

INSERT INTO rowcount (table_name, total_rows)
VALUES (
        'alertstate',
        (
            SELECT COUNT(*)
            FROM alertstate
        )
    );

COMMIT;
