CREATE TABLE IF NOT EXISTS sfacontroller (
    id serial PRIMARY KEY,
    INDEX integer NOT NULL,
    enclosure_index integer NOT NULL,
    health_state smallint NOT NULL,
    health_state_reason text NOT NULL,
    child_health_state smallint NOT NULL,
    storage_system text NOT NULL,
    CONSTRAINT sfacontroller_child_health_state_check CHECK ((child_health_state >= 0)),
    CONSTRAINT sfacontroller_enclosure_index_check CHECK ((enclosure_index >= 0)),
    CONSTRAINT sfacontroller_health_state_check CHECK ((health_state >= 0)),
    CONSTRAINT sfacontroller_index_check CHECK ((INDEX >= 0))
);

CREATE TABLE sfadiskdrive (
    id serial PRIMARY KEY,
    INDEX integer NOT NULL,
    enclosure_index integer NOT NULL,
    failed boolean NOT NULL,
    slot_number integer NOT NULL,
    health_state smallint NOT NULL,
    health_state_reason text NOT NULL,
    member_index smallint,
    member_state smallint NOT NULL,
    storage_system text NOT NULL,
    CONSTRAINT sfadiskdrive_enclosure_index_check CHECK ((enclosure_index >= 0)),
    CONSTRAINT sfadiskdrive_health_state_check CHECK ((health_state >= 0)),
    CONSTRAINT sfadiskdrive_index_check CHECK ((INDEX >= 0)),
    CONSTRAINT sfadiskdrive_member_index_check CHECK ((member_index >= 0)),
    CONSTRAINT sfadiskdrive_member_state_check CHECK ((member_state >= 0)),
    CONSTRAINT sfadiskdrive_slot_number_check CHECK ((slot_number >= 0))
);

CREATE TABLE IF NOT EXISTS sfadiskslot (
    id serial PRIMARY KEY,
    INDEX integer NOT NULL,
    enclosure_index integer NOT NULL,
    disk_drive_index integer NOT NULL,
    storage_system text NOT NULL,
    CONSTRAINT sfadiskslot_disk_drive_index_check CHECK ((disk_drive_index >= 0)),
    CONSTRAINT sfadiskslot_enclosure_index_check CHECK ((enclosure_index >= 0)),
    CONSTRAINT sfadiskslot_index_check CHECK ((INDEX >= 0))
);

CREATE TABLE IF NOT EXISTS sfaenclosure (
    id serial PRIMARY KEY,
    INDEX integer NOT NULL,
    element_name text NOT NULL,
    health_state smallint NOT NULL,
    health_state_reason text NOT NULL,
    child_health_state smallint NOT NULL,
    model text NOT NULL,
    "position" smallint NOT NULL,
    enclosure_type smallint NOT NULL,
    canister_location text NOT NULL,
    storage_system text NOT NULL,
    CONSTRAINT sfaenclosure_child_health_state_check CHECK ((child_health_state >= 0)),
    CONSTRAINT sfaenclosure_enclosure_type_check CHECK ((enclosure_type >= 0)),
    CONSTRAINT sfaenclosure_health_state_check CHECK ((health_state >= 0)),
    CONSTRAINT sfaenclosure_index_check CHECK ((INDEX >= 0)),
    CONSTRAINT sfaenclosure_position_check CHECK (("position" >= 0))
);

CREATE TABLE IF NOT EXISTS sfajob (
    id serial PRIMARY KEY,
    INDEX integer NOT NULL,
    sub_target_index integer,
    sub_target_type smallint,
    job_type smallint NOT NULL,
    state smallint NOT NULL,
    storage_system text NOT NULL,
    CONSTRAINT sfajob_index_check CHECK ((INDEX >= 0)),
    CONSTRAINT sfajob_job_type_check CHECK ((job_type >= 0)),
    CONSTRAINT sfajob_state_check CHECK ((state >= 0)),
    CONSTRAINT sfajob_sub_target_index_check CHECK ((sub_target_index >= 0)),
    CONSTRAINT sfajob_sub_target_type_check CHECK ((sub_target_type >= 0))
);

CREATE TABLE IF NOT EXISTS sfapowersupply (
    id serial PRIMARY KEY,
    INDEX integer NOT NULL,
    enclosure_index integer NOT NULL,
    health_state smallint NOT NULL,
    health_state_reason text NOT NULL,
    "position" smallint NOT NULL,
    storage_system text NOT NULL,
    CONSTRAINT sfapowersupply_enclosure_index_check CHECK ((enclosure_index >= 0)),
    CONSTRAINT sfapowersupply_health_state_check CHECK ((health_state >= 0)),
    CONSTRAINT sfapowersupply_index_check CHECK ((INDEX >= 0)),
    CONSTRAINT sfapowersupply_position_check CHECK (("position" >= 0))
);

CREATE TABLE IF NOT EXISTS sfastoragesystem (
    id serial PRIMARY KEY,
    uuid text NOT NULL,
    platform text NOT NULL,
    health_state_reason text NOT NULL,
    health_state smallint NOT NULL,
    child_health_state smallint NOT NULL,
    CONSTRAINT sfastoragesystem_child_health_state_check CHECK ((child_health_state >= 0)),
    CONSTRAINT sfastoragesystem_health_state_check CHECK ((health_state >= 0))
);

ALTER TABLE ONLY sfacontroller
ADD CONSTRAINT sfacontroller_index_storage_system_6f589bbb_uniq UNIQUE (INDEX, storage_system);

--
-- Name: sfadiskdrive sfadiskdrive_index_storage_system_0b718f36_uniq; Type: CONSTRAINT; Schema: public; Owner: chroma
--
ALTER TABLE ONLY sfadiskdrive
ADD CONSTRAINT sfadiskdrive_index_storage_system_0b718f36_uniq UNIQUE (INDEX, storage_system);

--
-- Name: sfadiskslot sfadiskslot_enclosure_index_disk_dri_18cd5509_uniq; Type: CONSTRAINT; Schema: public; Owner: chroma
--
ALTER TABLE ONLY sfadiskslot
ADD CONSTRAINT sfadiskslot_enclosure_index_disk_dri_18cd5509_uniq UNIQUE (
        enclosure_index,
        disk_drive_index,
        storage_system
    );

--
-- Name: sfaenclosure sfaenclosure_index_storage_system_c39d47d8_uniq; Type: CONSTRAINT; Schema: public; Owner: chroma
--
ALTER TABLE ONLY sfaenclosure
ADD CONSTRAINT sfaenclosure_index_storage_system_c39d47d8_uniq UNIQUE (INDEX, storage_system);

--
-- Name: sfajob sfajob_index_storage_system_c18577fc_uniq; Type: CONSTRAINT; Schema: public; Owner: chroma
--
ALTER TABLE ONLY sfajob
ADD CONSTRAINT sfajob_index_storage_system_c18577fc_uniq UNIQUE (INDEX, storage_system);

--
-- Name: sfapowersupply sfapowersupp_index_storage_system_enc_3f8ee25a_uniq; Type: CONSTRAINT; Schema: public; Owner: chroma
--
ALTER TABLE ONLY sfapowersupply
ADD CONSTRAINT sfapowersupp_index_storage_system_enc_3f8ee25a_uniq UNIQUE (INDEX, storage_system, enclosure_index);

--
-- Name: sfastoragesystem sfastoragesystem_uuid_key; Type: CONSTRAINT; Schema: public; Owner: chroma
--
ALTER TABLE ONLY sfastoragesystem
ADD CONSTRAINT sfastoragesystem_uuid_key UNIQUE (uuid);

--
-- Name: sfacontroller sfacontr_storage_system_06113f33_fk_chroma_co; Type: FK CONSTRAINT; Schema: public; Owner: chroma
--
ALTER TABLE ONLY sfacontroller
ADD CONSTRAINT sfacontr_storage_system_06113f33_fk_chroma_co FOREIGN KEY (storage_system) REFERENCES sfastoragesystem(uuid) DEFERRABLE INITIALLY DEFERRED;

--
-- Name: sfadiskdrive sfadiskd_storage_system_52fdceb1_fk_chroma_co; Type: FK CONSTRAINT; Schema: public; Owner: chroma
--
ALTER TABLE ONLY sfadiskdrive
ADD CONSTRAINT sfadiskd_storage_system_52fdceb1_fk_chroma_co FOREIGN KEY (storage_system) REFERENCES sfastoragesystem(uuid) DEFERRABLE INITIALLY DEFERRED;

--
-- Name: sfadiskslot sfadisks_storage_system_f662e861_fk_chroma_co; Type: FK CONSTRAINT; Schema: public; Owner: chroma
--
ALTER TABLE ONLY sfadiskslot
ADD CONSTRAINT sfadisks_storage_system_f662e861_fk_chroma_co FOREIGN KEY (storage_system) REFERENCES sfastoragesystem(uuid) DEFERRABLE INITIALLY DEFERRED;

--
-- Name: sfaenclosure sfaenclo_storage_system_0855d8a3_fk_chroma_co; Type: FK CONSTRAINT; Schema: public; Owner: chroma
--
ALTER TABLE ONLY sfaenclosure
ADD CONSTRAINT sfaenclo_storage_system_0855d8a3_fk_chroma_co FOREIGN KEY (storage_system) REFERENCES sfastoragesystem(uuid) DEFERRABLE INITIALLY DEFERRED;

--
-- Name: sfajob sfajob_storage_system_11b37678_fk_chroma_co; Type: FK CONSTRAINT; Schema: public; Owner: chroma
--
ALTER TABLE ONLY sfajob
ADD CONSTRAINT sfajob_storage_system_11b37678_fk_chroma_co FOREIGN KEY (storage_system) REFERENCES sfastoragesystem(uuid) DEFERRABLE INITIALLY DEFERRED;

--
-- Name: sfapowersupply sfapower_storage_system_0fe8a28f_fk_chroma_co; Type: FK CONSTRAINT; Schema: public; Owner: chroma
--
ALTER TABLE ONLY sfapowersupply
ADD CONSTRAINT sfapower_storage_system_0fe8a28f_fk_chroma_co FOREIGN KEY (storage_system) REFERENCES sfastoragesystem(uuid) DEFERRABLE INITIALLY DEFERRED;
