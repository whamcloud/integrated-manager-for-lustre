DROP TYPE IF EXISTS fs_type;

CREATE TYPE fs_type AS ENUM('zfs', 'ldiskfs');

ALTER TABLE IF EXISTS target
ADD COLUMN fs_type fs_type;
