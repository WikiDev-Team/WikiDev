PRAGMA foreign_keys = ON;

CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(120) NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    avatar_url TEXT NOT NULL DEFAULT '',
    hashed_password TEXT NOT NULL,
    token VARCHAR(64),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE passwordresettoken (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user(id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    used_at DATETIME,
    created_at DATETIME NOT NULL
);

CREATE TABLE friendship (
    id INTEGER PRIMARY KEY,
    requester_id INTEGER NOT NULL REFERENCES user(id),
    addressee_id INTEGER NOT NULL REFERENCES user(id),
    status VARCHAR(20) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT uq_friendship_direction UNIQUE (requester_id, addressee_id),
    CONSTRAINT ck_friendship_distinct_users CHECK (requester_id <> addressee_id)
);

CREATE TABLE language (
    id INTEGER PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    slug VARCHAR(90) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    official_url TEXT NOT NULL DEFAULT '',
    logo_url TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE tag (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    slug VARCHAR(60) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE folder (
    id INTEGER PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    slug VARCHAR(170) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    visibility VARCHAR(20) NOT NULL DEFAULT 'PRIVATE',
    author_id INTEGER REFERENCES user(id),
    parent_folder_id INTEGER REFERENCES folder(id),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE page (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL UNIQUE,
    page_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    visibility VARCHAR(20) NOT NULL DEFAULT 'PRIVATE',
    summary TEXT NOT NULL DEFAULT '',
    language_id INTEGER REFERENCES language(id),
    author_id INTEGER REFERENCES user(id),
    parent_page_id INTEGER REFERENCES page(id),
    folder_id INTEGER REFERENCES folder(id),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE pageshare (
    page_id INTEGER NOT NULL REFERENCES page(id),
    user_id INTEGER NOT NULL REFERENCES user(id),
    permission VARCHAR(20) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (page_id, user_id)
);

CREATE TABLE pagetaglink (
    page_id INTEGER NOT NULL REFERENCES page(id),
    tag_id INTEGER NOT NULL REFERENCES tag(id),
    PRIMARY KEY (page_id, tag_id)
);

CREATE TABLE pageblock (
    id INTEGER PRIMARY KEY,
    page_id INTEGER NOT NULL REFERENCES page(id),
    position INTEGER NOT NULL DEFAULT 0,
    block_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    language VARCHAR(50) NOT NULL DEFAULT '',
    font_size VARCHAR(20) NOT NULL DEFAULT 'normal',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE comment (
    id INTEGER PRIMARY KEY,
    page_id INTEGER NOT NULL REFERENCES page(id),
    author_id INTEGER REFERENCES user(id),
    block_id INTEGER REFERENCES pageblock(id),
    parent_comment_id INTEGER REFERENCES comment(id),
    body TEXT NOT NULL DEFAULT '',
    code TEXT,
    language VARCHAR(20),
    is_deleted BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE codeexample (
    id INTEGER PRIMARY KEY,
    page_id INTEGER NOT NULL REFERENCES page(id),
    author_id INTEGER REFERENCES user(id),
    title VARCHAR(200) NOT NULL DEFAULT '',
    code TEXT NOT NULL DEFAULT '',
    explanation TEXT NOT NULL DEFAULT '',
    language_hint VARCHAR(50) NOT NULL DEFAULT '',
    is_public BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
