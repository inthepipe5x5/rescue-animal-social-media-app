--
-- PostgreSQL database dump
--

-- Dumped from database version 14.13 (Ubuntu 14.13-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.13 (Ubuntu 14.13-0ubuntu0.22.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: lin_wsl
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO lin_wsl;

--
-- Name: matched_rescue_org; Type: TABLE; Schema: public; Owner: lin_wsl
--

CREATE TABLE public.matched_rescue_org (
    id integer NOT NULL,
    matched_user_id integer,
    matched_org_id integer,
    matched_pct integer NOT NULL,
    matched_datetime timestamp without time zone NOT NULL,
    followed_by_user_bool boolean
);


ALTER TABLE public.matched_rescue_org OWNER TO lin_wsl;

--
-- Name: matched_rescue_org_id_seq; Type: SEQUENCE; Schema: public; Owner: lin_wsl
--

CREATE SEQUENCE public.matched_rescue_org_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.matched_rescue_org_id_seq OWNER TO lin_wsl;

--
-- Name: matched_rescue_org_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lin_wsl
--

ALTER SEQUENCE public.matched_rescue_org_id_seq OWNED BY public.matched_rescue_org.id;


--
-- Name: rescueOrg; Type: TABLE; Schema: public; Owner: lin_wsl
--

CREATE TABLE public."rescueOrg" (
    id integer NOT NULL,
    name text NOT NULL
);


ALTER TABLE public."rescueOrg" OWNER TO lin_wsl;

--
-- Name: rescueOrg_id_seq; Type: SEQUENCE; Schema: public; Owner: lin_wsl
--

CREATE SEQUENCE public."rescueOrg_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public."rescueOrg_id_seq" OWNER TO lin_wsl;

--
-- Name: rescueOrg_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lin_wsl
--

ALTER SEQUENCE public."rescueOrg_id_seq" OWNED BY public."rescueOrg".id;


--
-- Name: user_animal_preferences; Type: TABLE; Schema: public; Owner: lin_wsl
--

CREATE TABLE public.user_animal_preferences (
    id integer NOT NULL,
    species character varying(20) NOT NULL,
    user_preference_name character varying(100) NOT NULL,
    user_preference_data jsonb,
    user_id integer
);


ALTER TABLE public.user_animal_preferences OWNER TO lin_wsl;

--
-- Name: user_animal_preferences_id_seq; Type: SEQUENCE; Schema: public; Owner: lin_wsl
--

CREATE SEQUENCE public.user_animal_preferences_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_animal_preferences_id_seq OWNER TO lin_wsl;

--
-- Name: user_animal_preferences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lin_wsl
--

ALTER SEQUENCE public.user_animal_preferences_id_seq OWNED BY public.user_animal_preferences.id;


--
-- Name: user_current_pets; Type: TABLE; Schema: public; Owner: lin_wsl
--

CREATE TABLE public.user_current_pets (
    id integer NOT NULL,
    user_id integer NOT NULL,
    user_has_pets boolean,
    pet_quantity integer,
    pet_type character varying[],
    pets_age character varying[],
    user_pets_has_medical_conditions boolean,
    user_pets_friendly_to_new_dogs boolean,
    user_pets_friendly_to_new_cats boolean,
    user_pets_friendly_to_new_birds boolean,
    user_pets_friendly_to_new_bunnies boolean,
    user_pets_friendly_to_new_misc_animal_types boolean
);


ALTER TABLE public.user_current_pets OWNER TO lin_wsl;

--
-- Name: user_location; Type: TABLE; Schema: public; Owner: lin_wsl
--

CREATE TABLE public.user_location (
    id integer NOT NULL,
    user_id integer,
    country character varying(2) NOT NULL,
    state character varying(2) NOT NULL,
    postal_code character varying(7),
    geolocation character varying(100),
    city character varying(100)
);


ALTER TABLE public.user_location OWNER TO lin_wsl;

--
-- Name: user_location_id_seq; Type: SEQUENCE; Schema: public; Owner: lin_wsl
--

CREATE SEQUENCE public.user_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_location_id_seq OWNER TO lin_wsl;

--
-- Name: user_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lin_wsl
--

ALTER SEQUENCE public.user_location_id_seq OWNED BY public.user_location.id;


--
-- Name: user_residence; Type: TABLE; Schema: public; Owner: lin_wsl
--

CREATE TABLE public.user_residence (
    id integer NOT NULL,
    user_id integer NOT NULL,
    is_urban boolean,
    is_rural boolean,
    dwelling_type character varying,
    dwelling_size character varying,
    potential_hazards_description character varying,
    has_yard boolean,
    has_pool boolean,
    has_fence_surrounding_dwelling boolean,
    has_doggie_door boolean
);


ALTER TABLE public.user_residence OWNER TO lin_wsl;

--
-- Name: user_resources; Type: TABLE; Schema: public; Owner: lin_wsl
--

CREATE TABLE public.user_resources (
    id integer NOT NULL,
    user_id integer NOT NULL,
    possesses_car boolean,
    possesses_valid_drivers_license boolean
);


ALTER TABLE public.user_resources OWNER TO lin_wsl;

--
-- Name: user_travel_preferences; Type: TABLE; Schema: public; Owner: lin_wsl
--

CREATE TABLE public.user_travel_preferences (
    id integer NOT NULL,
    user_id integer,
    distance_filter_preference integer,
    willing_to_fly_by_airplane boolean,
    willing_to_drive boolean,
    willing_to_carpool boolean,
    willing_to_volunteer_transport boolean
);


ALTER TABLE public.user_travel_preferences OWNER TO lin_wsl;

--
-- Name: user_travel_preferences_id_seq; Type: SEQUENCE; Schema: public; Owner: lin_wsl
--

CREATE SEQUENCE public.user_travel_preferences_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_travel_preferences_id_seq OWNER TO lin_wsl;

--
-- Name: user_travel_preferences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lin_wsl
--

ALTER SEQUENCE public.user_travel_preferences_id_seq OWNED BY public.user_travel_preferences.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: lin_wsl
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email text,
    username text,
    image_url text,
    header_image_url text,
    bio text,
    password text NOT NULL,
    rescue_action_type character varying[] DEFAULT ARRAY['volunteering'::text, 'donation'::text, 'adoption'::text, 'animal foster'::text],
    animal_types character varying[] DEFAULT ARRAY['dog'::text],
    registration_date timestamp without time zone
);


ALTER TABLE public.users OWNER TO lin_wsl;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: lin_wsl
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO lin_wsl;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lin_wsl
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: matched_rescue_org id; Type: DEFAULT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.matched_rescue_org ALTER COLUMN id SET DEFAULT nextval('public.matched_rescue_org_id_seq'::regclass);


--
-- Name: rescueOrg id; Type: DEFAULT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public."rescueOrg" ALTER COLUMN id SET DEFAULT nextval('public."rescueOrg_id_seq"'::regclass);


--
-- Name: user_animal_preferences id; Type: DEFAULT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_animal_preferences ALTER COLUMN id SET DEFAULT nextval('public.user_animal_preferences_id_seq'::regclass);


--
-- Name: user_location id; Type: DEFAULT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_location ALTER COLUMN id SET DEFAULT nextval('public.user_location_id_seq'::regclass);


--
-- Name: user_travel_preferences id; Type: DEFAULT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_travel_preferences ALTER COLUMN id SET DEFAULT nextval('public.user_travel_preferences_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: lin_wsl
--

INSERT INTO public.alembic_version (version_num) VALUES ('f1663474f27b');


--
-- Data for Name: matched_rescue_org; Type: TABLE DATA; Schema: public; Owner: lin_wsl
--



--
-- Data for Name: rescueOrg; Type: TABLE DATA; Schema: public; Owner: lin_wsl
--



--
-- Data for Name: user_animal_preferences; Type: TABLE DATA; Schema: public; Owner: lin_wsl
--



--
-- Data for Name: user_current_pets; Type: TABLE DATA; Schema: public; Owner: lin_wsl
--



--
-- Data for Name: user_location; Type: TABLE DATA; Schema: public; Owner: lin_wsl
--

INSERT INTO public.user_location (id, user_id, country, state, postal_code, geolocation, city) VALUES (1, NULL, 'CA', 'ON', 'm5j 0b3', '43.6429,79.3889', 'Toronto');


--
-- Data for Name: user_residence; Type: TABLE DATA; Schema: public; Owner: lin_wsl
--



--
-- Data for Name: user_resources; Type: TABLE DATA; Schema: public; Owner: lin_wsl
--



--
-- Data for Name: user_travel_preferences; Type: TABLE DATA; Schema: public; Owner: lin_wsl
--



--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: lin_wsl
--

INSERT INTO public.users (id, email, username, image_url, header_image_url, bio, password, rescue_action_type, animal_types, registration_date) VALUES (1, 'test123@test123.com', 'test123', '../static/images/profile-images/default-hero-sasha-sashina-YCsh4ltV9Ec-unsplash.jpg', '../static/images/profile-images/default-header-image-natalie-kinnear-MUkxOfl8epk-unsplash.jpg', 'test123', '$2b$12$wONIW4tokQE8cnfiO9BIZe40FAWEbP0QB11bAkL1gpSaQM7jE7Ao6', '{volunteering,donation,adoption,"animal foster"}', '{dog}', NULL);


--
-- Name: matched_rescue_org_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lin_wsl
--

SELECT pg_catalog.setval('public.matched_rescue_org_id_seq', 1, false);


--
-- Name: rescueOrg_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lin_wsl
--

SELECT pg_catalog.setval('public."rescueOrg_id_seq"', 1, false);


--
-- Name: user_animal_preferences_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lin_wsl
--

SELECT pg_catalog.setval('public.user_animal_preferences_id_seq', 15, true);


--
-- Name: user_location_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lin_wsl
--

SELECT pg_catalog.setval('public.user_location_id_seq', 1, true);


--
-- Name: user_travel_preferences_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lin_wsl
--

SELECT pg_catalog.setval('public.user_travel_preferences_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lin_wsl
--

SELECT pg_catalog.setval('public.users_id_seq', 1, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: matched_rescue_org matched_rescue_org_pkey; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.matched_rescue_org
    ADD CONSTRAINT matched_rescue_org_pkey PRIMARY KEY (id);


--
-- Name: rescueOrg rescueOrg_name_key; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public."rescueOrg"
    ADD CONSTRAINT "rescueOrg_name_key" UNIQUE (name);


--
-- Name: rescueOrg rescueOrg_pkey; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public."rescueOrg"
    ADD CONSTRAINT "rescueOrg_pkey" PRIMARY KEY (id);


--
-- Name: user_animal_preferences user_animal_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_animal_preferences
    ADD CONSTRAINT user_animal_preferences_pkey PRIMARY KEY (id);


--
-- Name: user_current_pets user_current_pets_id_key; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_current_pets
    ADD CONSTRAINT user_current_pets_id_key UNIQUE (id);


--
-- Name: user_current_pets user_current_pets_pkey; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_current_pets
    ADD CONSTRAINT user_current_pets_pkey PRIMARY KEY (id, user_id);


--
-- Name: user_current_pets user_current_pets_user_id_key; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_current_pets
    ADD CONSTRAINT user_current_pets_user_id_key UNIQUE (user_id);


--
-- Name: user_location user_location_pkey; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_location
    ADD CONSTRAINT user_location_pkey PRIMARY KEY (id);


--
-- Name: user_location user_location_user_id_key; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_location
    ADD CONSTRAINT user_location_user_id_key UNIQUE (user_id);


--
-- Name: user_residence user_residence_id_key; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_residence
    ADD CONSTRAINT user_residence_id_key UNIQUE (id);


--
-- Name: user_residence user_residence_pkey; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_residence
    ADD CONSTRAINT user_residence_pkey PRIMARY KEY (id, user_id);


--
-- Name: user_residence user_residence_user_id_key; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_residence
    ADD CONSTRAINT user_residence_user_id_key UNIQUE (user_id);


--
-- Name: user_resources user_resources_id_key; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_resources
    ADD CONSTRAINT user_resources_id_key UNIQUE (id);


--
-- Name: user_resources user_resources_pkey; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_resources
    ADD CONSTRAINT user_resources_pkey PRIMARY KEY (id, user_id);


--
-- Name: user_resources user_resources_user_id_key; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_resources
    ADD CONSTRAINT user_resources_user_id_key UNIQUE (user_id);


--
-- Name: user_travel_preferences user_travel_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_travel_preferences
    ADD CONSTRAINT user_travel_preferences_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: matched_rescue_org matched_rescue_org_matched_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.matched_rescue_org
    ADD CONSTRAINT matched_rescue_org_matched_org_id_fkey FOREIGN KEY (matched_org_id) REFERENCES public."rescueOrg"(id);


--
-- Name: matched_rescue_org matched_rescue_org_matched_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.matched_rescue_org
    ADD CONSTRAINT matched_rescue_org_matched_user_id_fkey FOREIGN KEY (matched_user_id) REFERENCES public.users(id);


--
-- Name: user_animal_preferences user_animal_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_animal_preferences
    ADD CONSTRAINT user_animal_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_location user_location_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_location
    ADD CONSTRAINT user_location_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_travel_preferences user_travel_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lin_wsl
--

ALTER TABLE ONLY public.user_travel_preferences
    ADD CONSTRAINT user_travel_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

