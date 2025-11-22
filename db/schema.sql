PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

create table error_codes (
    error_code_id integer primary key,
    error_code text not null
);

create table recommendation_templates (
    recommendation_template_id integer primary key,
    error_code_id integer references error_codes(error_code_id),
    template text not null
);

create table training_data (
    training_data_id integer primary key,
    label integer references recommendation_templates(recommendation_template_id),
    source_code text not null,
    error_text text not null
);

create table classification_models (
    classification_model_id integer primary key,
    name text not null,
    description text,
    path text not null,
    accuracy real not null,
    f1score real not null,
    rocauc real not null
);