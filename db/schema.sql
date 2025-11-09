PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

create table recommendation_templates (
    recommendation_template_id integer primary key,
    errorType text not null,
    template text not null
);

create table training_data (
    training_data integer primary key,
    label integer references recommendation_template(recommendation_template_id),
    sourceCode text not null,
    errorText text not null
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