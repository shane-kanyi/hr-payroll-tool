--
-- PostgreSQL database dump
--


-- Dumped from database version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)

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

ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_role_id_fkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_employee_id_fkey;
ALTER TABLE IF EXISTS ONLY public.payroll_periods DROP CONSTRAINT IF EXISTS payroll_periods_generated_by_id_fkey;
ALTER TABLE IF EXISTS ONLY public.payroll_entries DROP CONSTRAINT IF EXISTS payroll_entries_payroll_period_id_fkey;
ALTER TABLE IF EXISTS ONLY public.payroll_entries DROP CONSTRAINT IF EXISTS payroll_entries_employee_id_fkey;
ALTER TABLE IF EXISTS ONLY public.leave_requests DROP CONSTRAINT IF EXISTS leave_requests_employee_id_fkey;
ALTER TABLE IF EXISTS ONLY public.leave_requests DROP CONSTRAINT IF EXISTS leave_requests_decided_by_id_fkey;
ALTER TABLE IF EXISTS ONLY public.leave_balances DROP CONSTRAINT IF EXISTS leave_balances_employee_id_fkey;
ALTER TABLE IF EXISTS ONLY public.employees DROP CONSTRAINT IF EXISTS employees_team_id_fkey;
ALTER TABLE IF EXISTS ONLY public.employees DROP CONSTRAINT IF EXISTS employees_manager_id_fkey;
ALTER TABLE IF EXISTS ONLY public.audit_logs DROP CONSTRAINT IF EXISTS audit_logs_actor_user_id_fkey;
DROP INDEX IF EXISTS public.ix_users_email;
DROP INDEX IF EXISTS public.ix_payroll_entries_employee_id;
DROP INDEX IF EXISTS public.ix_leave_requests_status;
DROP INDEX IF EXISTS public.ix_leave_requests_employee_id;
DROP INDEX IF EXISTS public.ix_leave_requests_employee_dates;
DROP INDEX IF EXISTS public.ix_employees_team_id;
DROP INDEX IF EXISTS public.ix_employees_manager_id;
DROP INDEX IF EXISTS public.ix_employees_is_active;
DROP INDEX IF EXISTS public.ix_audit_logs_entity;
DROP INDEX IF EXISTS public.ix_audit_logs_created_at;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_employee_id_key;
ALTER TABLE IF EXISTS ONLY public.payroll_periods DROP CONSTRAINT IF EXISTS uq_payroll_period_year_month;
ALTER TABLE IF EXISTS ONLY public.payroll_entries DROP CONSTRAINT IF EXISTS uq_payroll_entry_period_employee;
ALTER TABLE IF EXISTS ONLY public.leave_balances DROP CONSTRAINT IF EXISTS uq_leave_balance_employee_type_year;
ALTER TABLE IF EXISTS ONLY public.teams DROP CONSTRAINT IF EXISTS teams_pkey;
ALTER TABLE IF EXISTS ONLY public.teams DROP CONSTRAINT IF EXISTS teams_name_key;
ALTER TABLE IF EXISTS ONLY public.roles DROP CONSTRAINT IF EXISTS roles_pkey;
ALTER TABLE IF EXISTS ONLY public.roles DROP CONSTRAINT IF EXISTS roles_name_key;
ALTER TABLE IF EXISTS ONLY public.payroll_periods DROP CONSTRAINT IF EXISTS payroll_periods_pkey;
ALTER TABLE IF EXISTS ONLY public.payroll_entries DROP CONSTRAINT IF EXISTS payroll_entries_pkey;
ALTER TABLE IF EXISTS ONLY public.leave_requests DROP CONSTRAINT IF EXISTS leave_requests_pkey;
ALTER TABLE IF EXISTS ONLY public.leave_balances DROP CONSTRAINT IF EXISTS leave_balances_pkey;
ALTER TABLE IF EXISTS ONLY public.employees DROP CONSTRAINT IF EXISTS employees_pkey;
ALTER TABLE IF EXISTS ONLY public.audit_logs DROP CONSTRAINT IF EXISTS audit_logs_pkey;
ALTER TABLE IF EXISTS ONLY public.alembic_version DROP CONSTRAINT IF EXISTS alembic_version_pkc;
ALTER TABLE IF EXISTS public.users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.teams ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.roles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.payroll_periods ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.payroll_entries ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.leave_requests ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.leave_balances ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.employees ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.audit_logs ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.users_id_seq;
DROP TABLE IF EXISTS public.users;
DROP SEQUENCE IF EXISTS public.teams_id_seq;
DROP TABLE IF EXISTS public.teams;
DROP SEQUENCE IF EXISTS public.roles_id_seq;
DROP TABLE IF EXISTS public.roles;
DROP SEQUENCE IF EXISTS public.payroll_periods_id_seq;
DROP TABLE IF EXISTS public.payroll_periods;
DROP SEQUENCE IF EXISTS public.payroll_entries_id_seq;
DROP TABLE IF EXISTS public.payroll_entries;
DROP SEQUENCE IF EXISTS public.leave_requests_id_seq;
DROP TABLE IF EXISTS public.leave_requests;
DROP SEQUENCE IF EXISTS public.leave_balances_id_seq;
DROP TABLE IF EXISTS public.leave_balances;
DROP SEQUENCE IF EXISTS public.employees_id_seq;
DROP TABLE IF EXISTS public.employees;
DROP SEQUENCE IF EXISTS public.audit_logs_id_seq;
DROP TABLE IF EXISTS public.audit_logs;
DROP TABLE IF EXISTS public.alembic_version;
DROP TYPE IF EXISTS public.payroll_period_status;
DROP TYPE IF EXISTS public.leave_type;
DROP TYPE IF EXISTS public.leave_status;
DROP TYPE IF EXISTS public.employment_type;
-- *not* dropping schema, since initdb creates it
--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


--
-- Name: employment_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.employment_type AS ENUM (
    'FULL_TIME',
    'PART_TIME',
    'CONTRACT'
);


--
-- Name: leave_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.leave_status AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'CANCELLED'
);


--
-- Name: leave_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.leave_type AS ENUM (
    'ANNUAL',
    'SICK',
    'UNPAID'
);


--
-- Name: payroll_period_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.payroll_period_status AS ENUM (
    'DRAFT',
    'FINALIZED'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    actor_user_id integer,
    action character varying(120) NOT NULL,
    entity_type character varying(60) NOT NULL,
    entity_id integer,
    extra_data json,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: employees; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.employees (
    id integer NOT NULL,
    name character varying(150) NOT NULL,
    role character varying(120) NOT NULL,
    team_id integer,
    manager_id integer,
    start_date date NOT NULL,
    salary numeric(12,2) NOT NULL,
    employment_type public.employment_type NOT NULL,
    is_active boolean NOT NULL,
    deactivated_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_employee_salary_non_negative CHECK ((salary >= (0)::numeric))
);


--
-- Name: employees_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.employees_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: employees_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.employees_id_seq OWNED BY public.employees.id;


--
-- Name: leave_balances; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.leave_balances (
    id integer NOT NULL,
    employee_id integer NOT NULL,
    leave_type public.leave_type NOT NULL,
    year integer NOT NULL,
    allocated_days numeric(5,2) NOT NULL,
    used_days numeric(5,2) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_leave_balance_allocated_non_negative CHECK ((allocated_days >= (0)::numeric)),
    CONSTRAINT ck_leave_balance_used_non_negative CHECK ((used_days >= (0)::numeric))
);


--
-- Name: leave_balances_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.leave_balances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: leave_balances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.leave_balances_id_seq OWNED BY public.leave_balances.id;


--
-- Name: leave_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.leave_requests (
    id integer NOT NULL,
    employee_id integer NOT NULL,
    leave_type public.leave_type NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    days_requested numeric(5,2) NOT NULL,
    status public.leave_status NOT NULL,
    reason text,
    requested_at timestamp with time zone NOT NULL,
    decided_by_id integer,
    decided_at timestamp with time zone,
    decision_notes text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    escalated_at timestamp with time zone,
    CONSTRAINT ck_leave_days_positive CHECK ((days_requested > (0)::numeric)),
    CONSTRAINT ck_leave_end_after_start CHECK ((end_date >= start_date))
);


--
-- Name: leave_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.leave_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: leave_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.leave_requests_id_seq OWNED BY public.leave_requests.id;


--
-- Name: payroll_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payroll_entries (
    id integer NOT NULL,
    payroll_period_id integer NOT NULL,
    employee_id integer NOT NULL,
    gross_salary numeric(12,2) NOT NULL,
    unpaid_leave_days numeric(5,2) NOT NULL,
    unpaid_leave_deduction numeric(12,2) NOT NULL,
    taxable_income numeric(12,2) NOT NULL,
    tax_deduction numeric(12,2) NOT NULL,
    social_security_deduction numeric(12,2) NOT NULL,
    net_salary numeric(12,2) NOT NULL,
    calculation_notes json,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_payroll_entry_gross_non_negative CHECK ((gross_salary >= (0)::numeric)),
    CONSTRAINT ck_payroll_entry_net_non_negative CHECK ((net_salary >= (0)::numeric))
);


--
-- Name: payroll_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payroll_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payroll_entries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.payroll_entries_id_seq OWNED BY public.payroll_entries.id;


--
-- Name: payroll_periods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payroll_periods (
    id integer NOT NULL,
    year integer NOT NULL,
    month integer NOT NULL,
    status public.payroll_period_status NOT NULL,
    generated_at timestamp with time zone,
    generated_by_id integer,
    finalized_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_payroll_period_month_range CHECK (((month >= 1) AND (month <= 12)))
);


--
-- Name: payroll_periods_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payroll_periods_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payroll_periods_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.payroll_periods_id_seq OWNED BY public.payroll_periods.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_roles_name_valid CHECK (((name)::text = ANY ((ARRAY['admin'::character varying, 'manager'::character varying, 'employee'::character varying])::text[])))
);


--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teams (
    id integer NOT NULL,
    name character varying(120) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: teams_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teams_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teams_id_seq OWNED BY public.teams.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    employee_id integer,
    role_id integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
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
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: employees id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.employees ALTER COLUMN id SET DEFAULT nextval('public.employees_id_seq'::regclass);


--
-- Name: leave_balances id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leave_balances ALTER COLUMN id SET DEFAULT nextval('public.leave_balances_id_seq'::regclass);


--
-- Name: leave_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leave_requests ALTER COLUMN id SET DEFAULT nextval('public.leave_requests_id_seq'::regclass);


--
-- Name: payroll_entries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payroll_entries ALTER COLUMN id SET DEFAULT nextval('public.payroll_entries_id_seq'::regclass);


--
-- Name: payroll_periods id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payroll_periods ALTER COLUMN id SET DEFAULT nextval('public.payroll_periods_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: teams id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams ALTER COLUMN id SET DEFAULT nextval('public.teams_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
598c1b53ccb8
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audit_logs (id, actor_user_id, action, entity_type, entity_id, extra_data, created_at) FROM stdin;
\.


--
-- Data for Name: employees; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.employees (id, name, role, team_id, manager_id, start_date, salary, employment_type, is_active, deactivated_at, created_at, updated_at) FROM stdin;
1	Grace Kim	Engineering Manager	1	\N	2019-03-01	7000.00	FULL_TIME	t	\N	2026-07-26 18:48:25.526164+03	2026-07-26 18:48:25.526169+03
2	Sam Patel	Sales Manager	2	\N	2019-06-01	6500.00	FULL_TIME	t	\N	2026-07-26 18:48:25.530351+03	2026-07-26 18:48:25.530354+03
3	Ravi Shah	Software Engineer	1	1	2021-09-15	4200.00	FULL_TIME	t	\N	2026-07-26 18:48:25.535207+03	2026-07-26 18:48:25.53521+03
4	Amara Okafor	Software Engineer	1	1	2022-01-10	3900.00	FULL_TIME	t	\N	2026-07-26 18:48:25.539798+03	2026-07-26 18:48:25.539801+03
5	Nina Fischer	Contract Designer	1	1	2023-04-01	2500.00	CONTRACT	t	\N	2026-07-26 18:48:25.543756+03	2026-07-26 18:48:25.543759+03
6	Leo Martins	Sales Executive	2	2	2020-11-01	3200.00	FULL_TIME	t	\N	2026-07-26 18:48:25.547256+03	2026-07-26 18:48:25.547259+03
7	Tom Reyes	Sales Executive (former)	2	2	2018-02-01	3000.00	FULL_TIME	f	2026-07-26 18:48:25.556916+03	2026-07-26 18:48:25.551606+03	2026-07-26 18:48:25.558002+03
\.


--
-- Data for Name: leave_balances; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.leave_balances (id, employee_id, leave_type, year, allocated_days, used_days, created_at, updated_at) FROM stdin;
1	3	ANNUAL	2026	21.00	3.00	2026-07-26 18:48:25.975526+03	2026-07-26 18:48:25.989875+03
2	5	ANNUAL	2026	21.00	0.00	2026-07-26 18:48:25.995376+03	2026-07-26 18:48:25.995386+03
3	4	SICK	2026	10.00	0.00	2026-07-26 18:48:26.005093+03	2026-07-26 18:48:26.005097+03
\.


--
-- Data for Name: leave_requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.leave_requests (id, employee_id, leave_type, start_date, end_date, days_requested, status, reason, requested_at, decided_by_id, decided_at, decision_notes, created_at, updated_at, escalated_at) FROM stdin;
1	3	ANNUAL	2026-07-31	2026-08-04	3.00	APPROVED	Family trip	2026-07-26 18:48:25.965201+03	1	2026-07-26 18:48:25.982033+03	Enjoy!	2026-07-26 18:48:25.977368+03	2026-07-26 18:48:25.990975+03	\N
2	5	ANNUAL	2026-08-03	2026-08-03	1.00	REJECTED	Long weekend	2026-07-26 18:48:25.993683+03	1	2026-07-26 18:48:25.999386+03	Two others already out that week	2026-07-26 18:48:25.996309+03	2026-07-26 18:48:26.000369+03	\N
3	4	SICK	2026-07-17	2026-07-17	1.00	PENDING	\N	2026-07-16 18:48:26.001949+03	\N	\N	\N	2026-07-26 18:48:26.006153+03	2026-07-26 18:48:26.010071+03	2026-07-26 18:48:26.007801+03
4	6	UNPAID	2026-06-08	2026-06-10	3.00	APPROVED	Unpaid personal leave	2026-07-26 18:48:26.013583+03	2	2026-07-26 18:48:26.018516+03	\N	2026-07-26 18:48:26.014735+03	2026-07-26 18:48:26.023852+03	\N
\.


--
-- Data for Name: payroll_entries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.payroll_entries (id, payroll_period_id, employee_id, gross_salary, unpaid_leave_days, unpaid_leave_deduction, taxable_income, tax_deduction, social_security_deduction, net_salary, calculation_notes, created_at, updated_at) FROM stdin;
1	1	4	3900.00	0.00	0.00	3900.00	380.00	234.00	3286.00	{"period_start": "2026-06-01", "period_end": "2026-06-30", "effective_start": "2026-06-01", "effective_end": "2026-06-30", "calendar_days_in_period": 30, "working_days_in_month": "22", "proration_factor": "1", "daily_rate_for_leave": "177.27", "social_security_rate": 0.06, "tax_breakdown": [{"band_lower": "0.00", "band_upper": "1000.00", "rate": 0.0, "amount_taxed": "1000.00", "tax": "0.00"}, {"band_lower": "1000.00", "band_upper": "3000.00", "rate": 0.1, "amount_taxed": "2000.00", "tax": "200.00"}, {"band_lower": "3000.00", "band_upper": "6000.00", "rate": 0.2, "amount_taxed": "900.00", "tax": "180.00"}]}	2026-07-26 18:48:26.034897+03	2026-07-26 18:48:26.0349+03
2	1	1	7000.00	0.00	0.00	7000.00	1050.00	420.00	5530.00	{"period_start": "2026-06-01", "period_end": "2026-06-30", "effective_start": "2026-06-01", "effective_end": "2026-06-30", "calendar_days_in_period": 30, "working_days_in_month": "22", "proration_factor": "1", "daily_rate_for_leave": "318.18", "social_security_rate": 0.06, "tax_breakdown": [{"band_lower": "0.00", "band_upper": "1000.00", "rate": 0.0, "amount_taxed": "1000.00", "tax": "0.00"}, {"band_lower": "1000.00", "band_upper": "3000.00", "rate": 0.1, "amount_taxed": "2000.00", "tax": "200.00"}, {"band_lower": "3000.00", "band_upper": "6000.00", "rate": 0.2, "amount_taxed": "3000.00", "tax": "600.00"}, {"band_lower": "6000.00", "band_upper": null, "rate": 0.25, "amount_taxed": "1000.00", "tax": "250.00"}]}	2026-07-26 18:48:26.038239+03	2026-07-26 18:48:26.038243+03
3	1	6	3200.00	3.00	436.36	2763.64	176.36	165.82	2421.46	{"period_start": "2026-06-01", "period_end": "2026-06-30", "effective_start": "2026-06-01", "effective_end": "2026-06-30", "calendar_days_in_period": 30, "working_days_in_month": "22", "proration_factor": "1", "daily_rate_for_leave": "145.45", "social_security_rate": 0.06, "tax_breakdown": [{"band_lower": "0.00", "band_upper": "1000.00", "rate": 0.0, "amount_taxed": "1000.00", "tax": "0.00"}, {"band_lower": "1000.00", "band_upper": "3000.00", "rate": 0.1, "amount_taxed": "1763.64", "tax": "176.36"}]}	2026-07-26 18:48:26.041061+03	2026-07-26 18:48:26.041064+03
4	1	5	2500.00	0.00	0.00	2500.00	150.00	150.00	2200.00	{"period_start": "2026-06-01", "period_end": "2026-06-30", "effective_start": "2026-06-01", "effective_end": "2026-06-30", "calendar_days_in_period": 30, "working_days_in_month": "22", "proration_factor": "1", "daily_rate_for_leave": "113.64", "social_security_rate": 0.06, "tax_breakdown": [{"band_lower": "0.00", "band_upper": "1000.00", "rate": 0.0, "amount_taxed": "1000.00", "tax": "0.00"}, {"band_lower": "1000.00", "band_upper": "3000.00", "rate": 0.1, "amount_taxed": "1500.00", "tax": "150.00"}]}	2026-07-26 18:48:26.043781+03	2026-07-26 18:48:26.043821+03
5	1	3	4200.00	0.00	0.00	4200.00	440.00	252.00	3508.00	{"period_start": "2026-06-01", "period_end": "2026-06-30", "effective_start": "2026-06-01", "effective_end": "2026-06-30", "calendar_days_in_period": 30, "working_days_in_month": "22", "proration_factor": "1", "daily_rate_for_leave": "190.91", "social_security_rate": 0.06, "tax_breakdown": [{"band_lower": "0.00", "band_upper": "1000.00", "rate": 0.0, "amount_taxed": "1000.00", "tax": "0.00"}, {"band_lower": "1000.00", "band_upper": "3000.00", "rate": 0.1, "amount_taxed": "2000.00", "tax": "200.00"}, {"band_lower": "3000.00", "band_upper": "6000.00", "rate": 0.2, "amount_taxed": "1200.00", "tax": "240.00"}]}	2026-07-26 18:48:26.045585+03	2026-07-26 18:48:26.045588+03
6	1	2	6500.00	0.00	0.00	6500.00	925.00	390.00	5185.00	{"period_start": "2026-06-01", "period_end": "2026-06-30", "effective_start": "2026-06-01", "effective_end": "2026-06-30", "calendar_days_in_period": 30, "working_days_in_month": "22", "proration_factor": "1", "daily_rate_for_leave": "295.45", "social_security_rate": 0.06, "tax_breakdown": [{"band_lower": "0.00", "band_upper": "1000.00", "rate": 0.0, "amount_taxed": "1000.00", "tax": "0.00"}, {"band_lower": "1000.00", "band_upper": "3000.00", "rate": 0.1, "amount_taxed": "2000.00", "tax": "200.00"}, {"band_lower": "3000.00", "band_upper": "6000.00", "rate": 0.2, "amount_taxed": "3000.00", "tax": "600.00"}, {"band_lower": "6000.00", "band_upper": null, "rate": 0.25, "amount_taxed": "500.00", "tax": "125.00"}]}	2026-07-26 18:48:26.047453+03	2026-07-26 18:48:26.047457+03
7	1	7	3000.00	0.00	0.00	3000.00	200.00	180.00	2620.00	{"period_start": "2026-06-01", "period_end": "2026-06-30", "effective_start": "2026-06-01", "effective_end": "2026-06-30", "calendar_days_in_period": 30, "working_days_in_month": "22", "proration_factor": "1", "daily_rate_for_leave": "136.36", "social_security_rate": 0.06, "tax_breakdown": [{"band_lower": "0.00", "band_upper": "1000.00", "rate": 0.0, "amount_taxed": "1000.00", "tax": "0.00"}, {"band_lower": "1000.00", "band_upper": "3000.00", "rate": 0.1, "amount_taxed": "2000.00", "tax": "200.00"}]}	2026-07-26 18:48:26.049947+03	2026-07-26 18:48:26.049949+03
\.


--
-- Data for Name: payroll_periods; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.payroll_periods (id, year, month, status, generated_at, generated_by_id, finalized_at, created_at, updated_at) FROM stdin;
1	2026	6	FINALIZED	2026-07-26 18:48:26.026773+03	1	2026-07-26 18:48:26.055551+03	2026-07-26 18:48:26.029956+03	2026-07-26 18:48:26.056042+03
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.roles (id, name, created_at, updated_at) FROM stdin;
1	admin	2026-07-26 18:48:17.885415+03	2026-07-26 18:48:17.885419+03
2	manager	2026-07-26 18:48:25.565971+03	2026-07-26 18:48:25.565974+03
3	employee	2026-07-26 18:48:25.766985+03	2026-07-26 18:48:25.766988+03
\.


--
-- Data for Name: teams; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.teams (id, name, created_at, updated_at) FROM stdin;
1	Engineering	2026-07-26 18:48:25.5179+03	2026-07-26 18:48:25.517904+03
2	Sales	2026-07-26 18:48:25.517905+03	2026-07-26 18:48:25.517905+03
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, email, password_hash, employee_id, role_id, is_active, created_at, updated_at) FROM stdin;
1	admin@example.com	scrypt:32768:8:1$vdXhujrhwY8DN8hB$1fe80e799e1594d7d7ddfed7047d327691b0da7fcbf7a3084fd2df0af736a73df3aa2e89a2e0fd12e0686b9a990a9be59ea9c8bc3be4043f2f419d5fac5c94fa	\N	1	t	2026-07-26 18:48:17.98528+03	2026-07-26 18:48:17.985284+03
2	grace@example.com	scrypt:32768:8:1$UmlWNxKKGjsZAa9e$022237bfb5fab8bf3f4a4380941351996bdcec716d7a94c9e2dd9b21f51232679a33c7ad8a6d105a5e95da8ae644dcd3ebe38d20fae656ea42eadd1293f2dc29	1	2	t	2026-07-26 18:48:25.663469+03	2026-07-26 18:48:25.663505+03
3	sam@example.com	scrypt:32768:8:1$0EaECyc8Li2SkujZ$c4782663199dc97159136153f7e450c52b0bcb25b333c2d38f4272fe1ba90a150a716baab4a7fec586989f9701dfae7676f20a53239a6e12b379c377a850d234	2	2	t	2026-07-26 18:48:25.762081+03	2026-07-26 18:48:25.762084+03
4	ravi@example.com	scrypt:32768:8:1$Zt6eEhMGOKtXyhPL$2348a59e4344c54290ef2a0fcb39c3ba67e9a391023f93e97792622f450a4c947cf48be347688b28fb8ec8af3851b04d6d6f2b2d9a1d1977ba4b2a3af3854e8c	3	3	t	2026-07-26 18:48:25.86303+03	2026-07-26 18:48:25.863034+03
5	amara@example.com	scrypt:32768:8:1$up7qtcNv4JMJrkt3$941fdecfafbf446fa98f56f010639c97ee11bc760b44dc73ad4039c4031dabfa354040907e511fb18180ba4b10523fbd2c15c47c62364a60f32c0a896605ea43	4	3	t	2026-07-26 18:48:25.961996+03	2026-07-26 18:48:25.962+03
\.


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 1, false);


--
-- Name: employees_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.employees_id_seq', 7, true);


--
-- Name: leave_balances_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.leave_balances_id_seq', 3, true);


--
-- Name: leave_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.leave_requests_id_seq', 4, true);


--
-- Name: payroll_entries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.payroll_entries_id_seq', 7, true);


--
-- Name: payroll_periods_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.payroll_periods_id_seq', 1, true);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.roles_id_seq', 3, true);


--
-- Name: teams_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.teams_id_seq', 2, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 5, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: employees employees_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_pkey PRIMARY KEY (id);


--
-- Name: leave_balances leave_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leave_balances
    ADD CONSTRAINT leave_balances_pkey PRIMARY KEY (id);


--
-- Name: leave_requests leave_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leave_requests
    ADD CONSTRAINT leave_requests_pkey PRIMARY KEY (id);


--
-- Name: payroll_entries payroll_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payroll_entries
    ADD CONSTRAINT payroll_entries_pkey PRIMARY KEY (id);


--
-- Name: payroll_periods payroll_periods_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payroll_periods
    ADD CONSTRAINT payroll_periods_pkey PRIMARY KEY (id);


--
-- Name: roles roles_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: teams teams_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_name_key UNIQUE (name);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: leave_balances uq_leave_balance_employee_type_year; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leave_balances
    ADD CONSTRAINT uq_leave_balance_employee_type_year UNIQUE (employee_id, leave_type, year);


--
-- Name: payroll_entries uq_payroll_entry_period_employee; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payroll_entries
    ADD CONSTRAINT uq_payroll_entry_period_employee UNIQUE (payroll_period_id, employee_id);


--
-- Name: payroll_periods uq_payroll_period_year_month; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payroll_periods
    ADD CONSTRAINT uq_payroll_period_year_month UNIQUE (year, month);


--
-- Name: users users_employee_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_employee_id_key UNIQUE (employee_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_audit_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_created_at ON public.audit_logs USING btree (created_at);


--
-- Name: ix_audit_logs_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_entity ON public.audit_logs USING btree (entity_type, entity_id);


--
-- Name: ix_employees_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_employees_is_active ON public.employees USING btree (is_active);


--
-- Name: ix_employees_manager_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_employees_manager_id ON public.employees USING btree (manager_id);


--
-- Name: ix_employees_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_employees_team_id ON public.employees USING btree (team_id);


--
-- Name: ix_leave_requests_employee_dates; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leave_requests_employee_dates ON public.leave_requests USING btree (employee_id, start_date, end_date);


--
-- Name: ix_leave_requests_employee_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leave_requests_employee_id ON public.leave_requests USING btree (employee_id);


--
-- Name: ix_leave_requests_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leave_requests_status ON public.leave_requests USING btree (status);


--
-- Name: ix_payroll_entries_employee_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payroll_entries_employee_id ON public.payroll_entries USING btree (employee_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: audit_logs audit_logs_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(id);


--
-- Name: employees employees_manager_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES public.employees(id);


--
-- Name: employees employees_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- Name: leave_balances leave_balances_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leave_balances
    ADD CONSTRAINT leave_balances_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: leave_requests leave_requests_decided_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leave_requests
    ADD CONSTRAINT leave_requests_decided_by_id_fkey FOREIGN KEY (decided_by_id) REFERENCES public.employees(id);


--
-- Name: leave_requests leave_requests_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leave_requests
    ADD CONSTRAINT leave_requests_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: payroll_entries payroll_entries_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payroll_entries
    ADD CONSTRAINT payroll_entries_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: payroll_entries payroll_entries_payroll_period_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payroll_entries
    ADD CONSTRAINT payroll_entries_payroll_period_id_fkey FOREIGN KEY (payroll_period_id) REFERENCES public.payroll_periods(id);


--
-- Name: payroll_periods payroll_periods_generated_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payroll_periods
    ADD CONSTRAINT payroll_periods_generated_by_id_fkey FOREIGN KEY (generated_by_id) REFERENCES public.employees(id);


--
-- Name: users users_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- PostgreSQL database dump complete
--


