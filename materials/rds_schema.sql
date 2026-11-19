-- 入网体检 · RDS MySQL 建表脚本
--
-- 目标库：华为云 RDS for MySQL 8.0（CHECK 约束需 8.0.16 及以上才真正生效）
-- 字段契约来源：src/schema.py（Firmware / Evidence / Decision / Policy 四模型）
--                configs/anchors.yaml（anchor 表）、docs/00-总体框架.md §3.1（unpack_job 表）
-- 说明：
--   1. checks（检查项清单）不建表：唯一来源是 configs/baseline.yaml，证据里只存 check_code 文本。
--   2. 所有枚举取值必须与 src/schema.py 的枚举成员值逐字一致，改一处必须同步改另一处。
--   3. 全部使用 CREATE TABLE IF NOT EXISTS，便于重复执行而不报错。

SET NAMES utf8mb4;

-- ---- 固件身份 --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS firmware (
    id          VARCHAR(64)  NOT NULL COMMENT '固件主键，如 fw-0001',
    vendor      VARCHAR(64)  NOT NULL COMMENT '厂商',
    model       VARCHAR(128) NOT NULL COMMENT '型号（含硬件版本）',
    version     VARCHAR(128) NOT NULL COMMENT '固件版本字符串',
    -- 默认存 64 位十六进制；长度留余量以容纳未实测时的 TODO(measure) 占位串
    sha256      VARCHAR(128) NOT NULL COMMENT '固件 SHA-256（实测值）',
    source_url  VARCHAR(512) NOT NULL COMMENT '下载地址或本地路径',
    family      VARCHAR(128) NULL     COMMENT '谱系/同族标识，未聚类时为 NULL',
    PRIMARY KEY (id),
    KEY idx_firmware_vendor_model (vendor, model),
    KEY idx_firmware_sha256 (sha256)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '待体检固件身份';

-- ---- 证据（一条可追溯到原文的取证结果）------------------------------------
CREATE TABLE IF NOT EXISTS evidence (
    id          VARCHAR(64)  NOT NULL COMMENT '证据主键，如 ev-0001',
    firmware_id VARCHAR(64)  NOT NULL COMMENT '所属固件',
    check_code  VARCHAR(64)  NOT NULL COMMENT '检查项编码，取值见 configs/baseline.yaml',
    level       ENUM('E1', 'E2', 'E3') NOT NULL COMMENT '证据分层，与 EvidenceLevel 一致',
    confidence  DECIMAL(4, 3) NOT NULL COMMENT '置信度',
    raw_ref     VARCHAR(512) NOT NULL COMMENT '原文引用：报文/响应/文件路径',
    detail      TEXT         NOT NULL COMMENT '证据描述',
    PRIMARY KEY (id),
    KEY idx_evidence_firmware (firmware_id),
    KEY idx_evidence_check (check_code),
    CONSTRAINT fk_evidence_firmware FOREIGN KEY (firmware_id)
        REFERENCES firmware (id) ON DELETE CASCADE,
    CONSTRAINT ck_evidence_confidence CHECK (confidence >= 0 AND confidence <= 1)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '取证结果';

-- ---- 判定（每个固件一条）-------------------------------------------------
CREATE TABLE IF NOT EXISTS decision (
    firmware_id     VARCHAR(64) NOT NULL COMMENT '固件主键，一对一',
    verdict         ENUM('pass', 'conditional', 'reject') NOT NULL COMMENT '三态判定',
    confidence      DECIMAL(4, 3) NOT NULL COMMENT '判定置信度',
    exposure        DECIMAL(4, 3) NULL     COMMENT '风险敞口分，未计算时为 NULL',
    reasons_json    JSON NOT NULL COMMENT '判定理由列表（字符串数组）',
    evidence_ids_json JSON NOT NULL COMMENT '支撑该判定的证据 id 数组',
    PRIMARY KEY (firmware_id),
    CONSTRAINT fk_decision_firmware FOREIGN KEY (firmware_id)
        REFERENCES firmware (id) ON DELETE CASCADE,
    CONSTRAINT ck_decision_confidence CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT ck_decision_exposure CHECK (exposure IS NULL OR (exposure >= 0 AND exposure <= 1))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '放行判定';

-- ---- 策略（与判定同生命周期，每个固件一条）--------------------------------
CREATE TABLE IF NOT EXISTS policy (
    firmware_id   VARCHAR(64) NOT NULL COMMENT '固件主键，一对一',
    granularity   ENUM('fqdn', 'vendor-group', 'asn') NOT NULL COMMENT '下发粒度，与 Granularity 一致',
    rule_format   ENUM('acl', 'mud') NOT NULL COMMENT '载体格式，与 RuleFormat 一致',
    rules_json    JSON NOT NULL COMMENT '规则条目（字符串数组）',
    asn_fallback  TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否回退到 ASN 粒度',
    rollback_ref  VARCHAR(128) NULL COMMENT '回滚引用/快照标识，未生成时为 NULL',
    PRIMARY KEY (firmware_id),
    CONSTRAINT fk_policy_firmware FOREIGN KEY (firmware_id)
        REFERENCES firmware (id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '放行策略';

-- ---- 锚点（公开固件 + 公开漏洞 + 版本可对）--------------------------------
-- 对应 configs/anchors.yaml；verified 为 0 时其余版本类字段允许为 TBD 占位。
CREATE TABLE IF NOT EXISTS anchor (
    id        VARCHAR(16)  NOT NULL COMMENT '锚点编号，如 A1',
    vendor    VARCHAR(64)  NOT NULL COMMENT '厂商',
    model     VARCHAR(128) NOT NULL COMMENT '型号',
    firmware  VARCHAR(128) NOT NULL COMMENT '固件版本',
    download  VARCHAR(512) NOT NULL COMMENT '公开下载链接',
    verified  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否已核验版本可对',
    notes     TEXT         NOT NULL COMMENT '备注：已知问题、出处说明',
    PRIMARY KEY (id),
    KEY idx_anchor_vendor_model (vendor, model)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '锚点库';

-- ---- 解包任务（异步作业状态）---------------------------------------------
CREATE TABLE IF NOT EXISTS unpack_job (
    id          VARCHAR(64) NOT NULL COMMENT '作业主键',
    firmware_id VARCHAR(64) NOT NULL COMMENT '目标固件',
    status      ENUM('queued', 'running', 'done', 'failed') NOT NULL COMMENT '作业状态',
    started_at  DATETIME NULL COMMENT '开始时间，未开始为 NULL',
    finished_at DATETIME NULL COMMENT '结束时间，未结束为 NULL',
    log_ref     VARCHAR(512) NULL COMMENT '日志引用（对象存储路径或文件路径）',
    PRIMARY KEY (id),
    KEY idx_unpack_job_firmware_status (firmware_id, status),
    CONSTRAINT fk_unpack_job_firmware FOREIGN KEY (firmware_id)
        REFERENCES firmware (id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '固件解包/仿真作业';