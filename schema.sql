--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: actividad_carrera; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.actividad_carrera (
    actividad_id integer NOT NULL,
    carrera_id integer NOT NULL
);


--
-- Name: actividad_docente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.actividad_docente (
    actividad_id integer NOT NULL,
    docente_id integer NOT NULL
);


--
-- Name: actividades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.actividades (
    id integer NOT NULL,
    titulo character varying(200) NOT NULL,
    descripcion text NOT NULL,
    tipo character varying(20) NOT NULL,
    fecha_inicio timestamp with time zone NOT NULL,
    fecha_fin timestamp with time zone NOT NULL,
    lugar character varying(200) NOT NULL,
    creditos numeric(8,1) NOT NULL,
    cupo_max integer NOT NULL,
    estado character varying(20) NOT NULL,
    created_by integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    encuesta_obligatoria boolean DEFAULT true NOT NULL,
    preguntas json NOT NULL,
    reprogramada_corto_plazo boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_actividades_creditos_positivo_multiplo_medio CHECK (((creditos > (0)::numeric) AND ((creditos * (2)::numeric) = trunc((creditos * (2)::numeric)))))
);


--
-- Name: actividades_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.actividades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: actividades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.actividades_id_seq OWNED BY public.actividades.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: asistencia; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asistencia (
    id integer NOT NULL,
    actividad_id integer NOT NULL,
    user_id integer NOT NULL,
    validated_by integer,
    validated_at timestamp with time zone DEFAULT now() NOT NULL,
    estado_creditos character varying(30) DEFAULT 'acreditado'::character varying NOT NULL
);


--
-- Name: asistencia_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.asistencia_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: asistencia_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.asistencia_id_seq OWNED BY public.asistencia.id;


--
-- Name: carreras; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.carreras (
    id integer NOT NULL,
    nombre character varying(50) NOT NULL,
    creditos_requeridos integer NOT NULL,
    tipo_id integer NOT NULL
);


--
-- Name: carreras_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.carreras_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: carreras_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.carreras_id_seq OWNED BY public.carreras.id;


--
-- Name: docentes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.docentes (
    id integer NOT NULL,
    persona_id integer NOT NULL
);


--
-- Name: docentes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.docentes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: docentes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.docentes_id_seq OWNED BY public.docentes.id;


--
-- Name: estudiantes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.estudiantes (
    user_id integer NOT NULL,
    carrera_id integer,
    creditos_acreditados double precision DEFAULT 0 NOT NULL,
    creditos_requeridos double precision DEFAULT 10 NOT NULL,
    creditos_penalizacion double precision DEFAULT 0 NOT NULL,
    CONSTRAINT ck_estudiante_creditos_acreditados CHECK ((creditos_acreditados >= (0)::double precision)),
    CONSTRAINT ck_estudiante_creditos_penalizacion CHECK ((creditos_penalizacion >= (0)::double precision)),
    CONSTRAINT ck_estudiante_creditos_requeridos CHECK ((creditos_requeridos > (0)::double precision))
);


--
-- Name: faq; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.faq (
    id integer NOT NULL,
    pregunta character varying(300) NOT NULL,
    respuesta text NOT NULL,
    tags text DEFAULT ''::text NOT NULL,
    categoria_id integer
);


--
-- Name: faq_categorias; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.faq_categorias (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL
);


--
-- Name: faq_categorias_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.faq_categorias_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: faq_categorias_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.faq_categorias_id_seq OWNED BY public.faq_categorias.id;


--
-- Name: faq_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.faq_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: faq_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.faq_id_seq OWNED BY public.faq.id;


--
-- Name: inscripciones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inscripciones (
    id integer NOT NULL,
    actividad_id integer NOT NULL,
    user_id integer NOT NULL,
    estado character varying(20) NOT NULL,
    reminded boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    baja_penalizada boolean DEFAULT false NOT NULL
);


--
-- Name: inscripciones_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inscripciones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inscripciones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.inscripciones_id_seq OWNED BY public.inscripciones.id;


--
-- Name: mensaje_lecturas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mensaje_lecturas (
    mensaje_id integer NOT NULL,
    user_id integer NOT NULL,
    leido boolean DEFAULT true NOT NULL,
    leido_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: mensajes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mensajes (
    id integer NOT NULL,
    remitente_id integer NOT NULL,
    destinatario_id integer,
    asunto character varying(200) NOT NULL,
    cuerpo text NOT NULL,
    leido boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    reply_to_id integer
);


--
-- Name: mensajes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.mensajes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mensajes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.mensajes_id_seq OWNED BY public.mensajes.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    user_id integer NOT NULL,
    mensaje character varying(500) NOT NULL,
    leido boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: password_resets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_resets (
    user_id integer NOT NULL,
    code_digest character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: personas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.personas (
    id integer NOT NULL,
    nombre character varying(120) NOT NULL,
    apellido character varying(120) NOT NULL,
    email character varying(120),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: personas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.personas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: personas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.personas_id_seq OWNED BY public.personas.id;


--
-- Name: respuestas_encuesta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.respuestas_encuesta (
    id integer NOT NULL,
    actividad_id integer NOT NULL,
    rating integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    respuestas json NOT NULL,
    estudiante_id integer NOT NULL
);


--
-- Name: sesiones_asistencia; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sesiones_asistencia (
    id integer NOT NULL,
    actividad_id integer NOT NULL,
    token character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_by integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: sesiones_asistencia_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sesiones_asistencia_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sesiones_asistencia_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sesiones_asistencia_id_seq OWNED BY public.sesiones_asistencia.id;


--
-- Name: survey_responses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.survey_responses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: survey_responses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.survey_responses_id_seq OWNED BY public.respuestas_encuesta.id;


--
-- Name: tipos_carrera; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tipos_carrera (
    id integer NOT NULL,
    nombre character varying(50) NOT NULL
);


--
-- Name: tipos_carrera_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tipos_carrera_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipos_carrera_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tipos_carrera_id_seq OWNED BY public.tipos_carrera.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    pw_hash character varying(255) NOT NULL,
    rol character varying(20) NOT NULL,
    debe_cambiar_pw boolean DEFAULT true NOT NULL,
    persona_id integer NOT NULL
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: ventanas_asistencia; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ventanas_asistencia (
    id integer NOT NULL,
    actividad_id integer NOT NULL,
    codigo character varying(64) NOT NULL,
    codigo_cierre character varying(128) NOT NULL,
    cerrada_manualmente boolean DEFAULT false NOT NULL,
    correos_enviados text DEFAULT '[]'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: ventanas_asistencia_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ventanas_asistencia_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ventanas_asistencia_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ventanas_asistencia_id_seq OWNED BY public.ventanas_asistencia.id;


--
-- Name: actividades id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividades ALTER COLUMN id SET DEFAULT nextval('public.actividades_id_seq'::regclass);


--
-- Name: asistencia id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asistencia ALTER COLUMN id SET DEFAULT nextval('public.asistencia_id_seq'::regclass);


--
-- Name: carreras id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carreras ALTER COLUMN id SET DEFAULT nextval('public.carreras_id_seq'::regclass);


--
-- Name: docentes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.docentes ALTER COLUMN id SET DEFAULT nextval('public.docentes_id_seq'::regclass);


--
-- Name: faq id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.faq ALTER COLUMN id SET DEFAULT nextval('public.faq_id_seq'::regclass);


--
-- Name: faq_categorias id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.faq_categorias ALTER COLUMN id SET DEFAULT nextval('public.faq_categorias_id_seq'::regclass);


--
-- Name: inscripciones id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inscripciones ALTER COLUMN id SET DEFAULT nextval('public.inscripciones_id_seq'::regclass);


--
-- Name: mensajes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes ALTER COLUMN id SET DEFAULT nextval('public.mensajes_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: personas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personas ALTER COLUMN id SET DEFAULT nextval('public.personas_id_seq'::regclass);


--
-- Name: respuestas_encuesta id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.respuestas_encuesta ALTER COLUMN id SET DEFAULT nextval('public.survey_responses_id_seq'::regclass);


--
-- Name: sesiones_asistencia id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesiones_asistencia ALTER COLUMN id SET DEFAULT nextval('public.sesiones_asistencia_id_seq'::regclass);


--
-- Name: tipos_carrera id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipos_carrera ALTER COLUMN id SET DEFAULT nextval('public.tipos_carrera_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: ventanas_asistencia id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ventanas_asistencia ALTER COLUMN id SET DEFAULT nextval('public.ventanas_asistencia_id_seq'::regclass);


--
-- Name: actividad_carrera actividad_carrera_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividad_carrera
    ADD CONSTRAINT actividad_carrera_pkey PRIMARY KEY (actividad_id, carrera_id);


--
-- Name: actividad_docente actividad_docente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividad_docente
    ADD CONSTRAINT actividad_docente_pkey PRIMARY KEY (actividad_id, docente_id);


--
-- Name: actividades actividades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividades
    ADD CONSTRAINT actividades_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: asistencia asistencia_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asistencia
    ADD CONSTRAINT asistencia_pkey PRIMARY KEY (id);


--
-- Name: carreras carreras_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carreras
    ADD CONSTRAINT carreras_nombre_key UNIQUE (nombre);


--
-- Name: carreras carreras_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carreras
    ADD CONSTRAINT carreras_pkey PRIMARY KEY (id);


--
-- Name: docentes docentes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.docentes
    ADD CONSTRAINT docentes_pkey PRIMARY KEY (id);


--
-- Name: estudiantes estudiantes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.estudiantes
    ADD CONSTRAINT estudiantes_pkey PRIMARY KEY (user_id);


--
-- Name: faq_categorias faq_categorias_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.faq_categorias
    ADD CONSTRAINT faq_categorias_nombre_key UNIQUE (nombre);


--
-- Name: faq_categorias faq_categorias_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.faq_categorias
    ADD CONSTRAINT faq_categorias_pkey PRIMARY KEY (id);


--
-- Name: faq faq_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.faq
    ADD CONSTRAINT faq_pkey PRIMARY KEY (id);


--
-- Name: inscripciones inscripciones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inscripciones
    ADD CONSTRAINT inscripciones_pkey PRIMARY KEY (id);


--
-- Name: mensaje_lecturas mensaje_lecturas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensaje_lecturas
    ADD CONSTRAINT mensaje_lecturas_pkey PRIMARY KEY (mensaje_id, user_id);


--
-- Name: mensajes mensajes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes
    ADD CONSTRAINT mensajes_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: password_resets password_resets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_pkey PRIMARY KEY (user_id);


--
-- Name: personas personas_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_email_key UNIQUE (email);


--
-- Name: personas personas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_pkey PRIMARY KEY (id);


--
-- Name: sesiones_asistencia sesiones_asistencia_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesiones_asistencia
    ADD CONSTRAINT sesiones_asistencia_pkey PRIMARY KEY (id);


--
-- Name: respuestas_encuesta survey_responses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.respuestas_encuesta
    ADD CONSTRAINT survey_responses_pkey PRIMARY KEY (id);


--
-- Name: tipos_carrera tipos_carrera_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipos_carrera
    ADD CONSTRAINT tipos_carrera_nombre_key UNIQUE (nombre);


--
-- Name: tipos_carrera tipos_carrera_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipos_carrera
    ADD CONSTRAINT tipos_carrera_pkey PRIMARY KEY (id);


--
-- Name: asistencia uq_asistencia_actividad_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asistencia
    ADD CONSTRAINT uq_asistencia_actividad_user UNIQUE (actividad_id, user_id);


--
-- Name: docentes uq_docentes_persona_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.docentes
    ADD CONSTRAINT uq_docentes_persona_id UNIQUE (persona_id);


--
-- Name: inscripciones uq_enroll_actividad_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inscripciones
    ADD CONSTRAINT uq_enroll_actividad_user UNIQUE (actividad_id, user_id);


--
-- Name: users uq_users_persona_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_persona_id UNIQUE (persona_id);


--
-- Name: ventanas_asistencia uq_ventana_asistencia_actividad; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ventanas_asistencia
    ADD CONSTRAINT uq_ventana_asistencia_actividad UNIQUE (actividad_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ventanas_asistencia ventanas_asistencia_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ventanas_asistencia
    ADD CONSTRAINT ventanas_asistencia_pkey PRIMARY KEY (id);


--
-- Name: ix_actividades_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_actividades_estado ON public.actividades USING btree (estado);


--
-- Name: ix_actividades_fecha_inicio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_actividades_fecha_inicio ON public.actividades USING btree (fecha_inicio);


--
-- Name: ix_asistencia_actividad_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_asistencia_actividad_id ON public.asistencia USING btree (actividad_id);


--
-- Name: ix_asistencia_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_asistencia_user_id ON public.asistencia USING btree (user_id);


--
-- Name: ix_docentes_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_docentes_id ON public.docentes USING btree (id);


--
-- Name: ix_estudiantes_carrera_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_estudiantes_carrera_id ON public.estudiantes USING btree (carrera_id);


--
-- Name: ix_faq_categoria_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_faq_categoria_id ON public.faq USING btree (categoria_id);


--
-- Name: ix_inscripciones_actividad_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inscripciones_actividad_id ON public.inscripciones USING btree (actividad_id);


--
-- Name: ix_inscripciones_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inscripciones_estado ON public.inscripciones USING btree (estado);


--
-- Name: ix_inscripciones_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inscripciones_user_id ON public.inscripciones USING btree (user_id);


--
-- Name: ix_mensajes_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mensajes_created_at ON public.mensajes USING btree (created_at);


--
-- Name: ix_mensajes_destinatario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mensajes_destinatario_id ON public.mensajes USING btree (destinatario_id);


--
-- Name: ix_mensajes_remitente_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mensajes_remitente_id ON public.mensajes USING btree (remitente_id);


--
-- Name: ix_mensajes_reply_to_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mensajes_reply_to_id ON public.mensajes USING btree (reply_to_id);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: ix_personas_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_personas_id ON public.personas USING btree (id);


--
-- Name: ix_respuestas_encuesta_actividad_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_respuestas_encuesta_actividad_id ON public.respuestas_encuesta USING btree (actividad_id);


--
-- Name: ix_sesiones_asistencia_actividad_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sesiones_asistencia_actividad_id ON public.sesiones_asistencia USING btree (actividad_id);


--
-- Name: ix_sesiones_asistencia_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_sesiones_asistencia_token ON public.sesiones_asistencia USING btree (token);


--
-- Name: ix_users_rol; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_rol ON public.users USING btree (rol);


--
-- Name: ix_ventanas_asistencia_actividad_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ventanas_asistencia_actividad_id ON public.ventanas_asistencia USING btree (actividad_id);


--
-- Name: ix_ventanas_asistencia_codigo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_ventanas_asistencia_codigo ON public.ventanas_asistencia USING btree (codigo);


--
-- Name: ix_ventanas_asistencia_codigo_cierre; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_ventanas_asistencia_codigo_cierre ON public.ventanas_asistencia USING btree (codigo_cierre);


--
-- Name: uq_respuesta_actividad_estudiante; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_respuesta_actividad_estudiante ON public.respuestas_encuesta USING btree (actividad_id, estudiante_id);


--
-- Name: actividad_carrera actividad_carrera_actividad_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividad_carrera
    ADD CONSTRAINT actividad_carrera_actividad_id_fkey FOREIGN KEY (actividad_id) REFERENCES public.actividades(id) ON DELETE CASCADE;


--
-- Name: actividad_carrera actividad_carrera_carrera_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividad_carrera
    ADD CONSTRAINT actividad_carrera_carrera_id_fkey FOREIGN KEY (carrera_id) REFERENCES public.carreras(id) ON DELETE CASCADE;


--
-- Name: actividad_docente actividad_docente_actividad_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividad_docente
    ADD CONSTRAINT actividad_docente_actividad_id_fkey FOREIGN KEY (actividad_id) REFERENCES public.actividades(id) ON DELETE CASCADE;


--
-- Name: actividad_docente actividad_docente_docente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividad_docente
    ADD CONSTRAINT actividad_docente_docente_id_fkey FOREIGN KEY (docente_id) REFERENCES public.docentes(id) ON DELETE CASCADE;


--
-- Name: actividades actividades_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividades
    ADD CONSTRAINT actividades_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: asistencia asistencia_actividad_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asistencia
    ADD CONSTRAINT asistencia_actividad_id_fkey FOREIGN KEY (actividad_id) REFERENCES public.actividades(id);


--
-- Name: asistencia asistencia_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asistencia
    ADD CONSTRAINT asistencia_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: asistencia asistencia_validated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asistencia
    ADD CONSTRAINT asistencia_validated_by_fkey FOREIGN KEY (validated_by) REFERENCES public.users(id);


--
-- Name: carreras carreras_tipo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carreras
    ADD CONSTRAINT carreras_tipo_id_fkey FOREIGN KEY (tipo_id) REFERENCES public.tipos_carrera(id);


--
-- Name: estudiantes estudiantes_carrera_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.estudiantes
    ADD CONSTRAINT estudiantes_carrera_id_fkey FOREIGN KEY (carrera_id) REFERENCES public.carreras(id) ON DELETE SET NULL;


--
-- Name: estudiantes estudiantes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.estudiantes
    ADD CONSTRAINT estudiantes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: docentes fk_docentes_persona; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.docentes
    ADD CONSTRAINT fk_docentes_persona FOREIGN KEY (persona_id) REFERENCES public.personas(id) ON DELETE CASCADE;


--
-- Name: faq fk_faq_categoria_id_faq_categorias; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.faq
    ADD CONSTRAINT fk_faq_categoria_id_faq_categorias FOREIGN KEY (categoria_id) REFERENCES public.faq_categorias(id) ON DELETE SET NULL;


--
-- Name: respuestas_encuesta fk_respuestas_encuesta_estudiante; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.respuestas_encuesta
    ADD CONSTRAINT fk_respuestas_encuesta_estudiante FOREIGN KEY (estudiante_id) REFERENCES public.estudiantes(user_id) ON DELETE CASCADE;


--
-- Name: users fk_users_persona_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_users_persona_id FOREIGN KEY (persona_id) REFERENCES public.personas(id) ON DELETE CASCADE;


--
-- Name: inscripciones inscripciones_actividad_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inscripciones
    ADD CONSTRAINT inscripciones_actividad_id_fkey FOREIGN KEY (actividad_id) REFERENCES public.actividades(id);


--
-- Name: inscripciones inscripciones_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inscripciones
    ADD CONSTRAINT inscripciones_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: mensaje_lecturas mensaje_lecturas_mensaje_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensaje_lecturas
    ADD CONSTRAINT mensaje_lecturas_mensaje_id_fkey FOREIGN KEY (mensaje_id) REFERENCES public.mensajes(id) ON DELETE CASCADE;


--
-- Name: mensaje_lecturas mensaje_lecturas_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensaje_lecturas
    ADD CONSTRAINT mensaje_lecturas_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: mensajes mensajes_destinatario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes
    ADD CONSTRAINT mensajes_destinatario_id_fkey FOREIGN KEY (destinatario_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: mensajes mensajes_remitente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes
    ADD CONSTRAINT mensajes_remitente_id_fkey FOREIGN KEY (remitente_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: mensajes mensajes_reply_to_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes
    ADD CONSTRAINT mensajes_reply_to_id_fkey FOREIGN KEY (reply_to_id) REFERENCES public.mensajes(id) ON DELETE SET NULL;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: password_resets password_resets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: sesiones_asistencia sesiones_asistencia_actividad_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesiones_asistencia
    ADD CONSTRAINT sesiones_asistencia_actividad_id_fkey FOREIGN KEY (actividad_id) REFERENCES public.actividades(id);


--
-- Name: sesiones_asistencia sesiones_asistencia_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesiones_asistencia
    ADD CONSTRAINT sesiones_asistencia_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: respuestas_encuesta survey_responses_actividad_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.respuestas_encuesta
    ADD CONSTRAINT survey_responses_actividad_id_fkey FOREIGN KEY (actividad_id) REFERENCES public.actividades(id);


--
-- Name: ventanas_asistencia ventanas_asistencia_actividad_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ventanas_asistencia
    ADD CONSTRAINT ventanas_asistencia_actividad_id_fkey FOREIGN KEY (actividad_id) REFERENCES public.actividades(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

