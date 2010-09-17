--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: chanclasses; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE chanclasses (
    chanclass bigint,
    classname character varying
);


ALTER TABLE public.chanclasses OWNER TO postgres;

--
-- Name: channels; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE channels (
    chanid bigint NOT NULL,
    name character varying,
    created timestamp without time zone DEFAULT now(),
    postable boolean,
    createdby bigint DEFAULT 0,
    chanclass bigint DEFAULT 0
);


ALTER TABLE public.channels OWNER TO postgres;

--
-- Name: channels_chanid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE channels_chanid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.channels_chanid_seq OWNER TO postgres;

--
-- Name: channels_chanid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE channels_chanid_seq OWNED BY channels.chanid;


--
-- Name: commentgroups; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE commentgroups (
    commentgroupid bigint NOT NULL,
    commentgrouptime timestamp without time zone DEFAULT now(),
    url character varying,
    cachedreplycount bigint DEFAULT 0
);


ALTER TABLE public.commentgroups OWNER TO postgres;

--
-- Name: commmentgroup_commentgroupid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE commmentgroup_commentgroupid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.commmentgroup_commentgroupid_seq OWNER TO postgres;

--
-- Name: commmentgroup_commentgroupid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE commmentgroup_commentgroupid_seq OWNED BY commentgroups.commentgroupid;


--
-- Name: feeds; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE feeds (
    url character varying,
    freq bigint DEFAULT 3000,
    feedid bigint NOT NULL,
    lasttime timestamp without time zone DEFAULT now(),
    feedclass bigint,
    usr bigint,
    channel bigint,
    feedname character varying,
    lastupdated timestamp without time zone
);


ALTER TABLE public.feeds OWNER TO postgres;

--
-- Name: feeds_feedid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE feeds_feedid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.feeds_feedid_seq OWNER TO postgres;

--
-- Name: feeds_feedid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE feeds_feedid_seq OWNED BY feeds.feedid;


--
-- Name: msgs; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE msgs (
    msgid bigint NOT NULL,
    sendid bigint,
    recvid bigint,
    msgtime timestamp without time zone DEFAULT now(),
    text character varying,
    title character varying
);


ALTER TABLE public.msgs OWNER TO postgres;

--
-- Name: msg_msgid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE msg_msgid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.msg_msgid_seq OWNER TO postgres;

--
-- Name: msg_msgid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE msg_msgid_seq OWNED BY msgs.msgid;


--
-- Name: replies; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE replies (
    replyid bigint NOT NULL,
    usr bigint,
    replytime timestamp without time zone DEFAULT now(),
    parent bigint,
    title character varying,
    text character varying,
    name character varying,
    score bigint DEFAULT 0,
    commentgroup bigint,
    lastedit timestamp without time zone DEFAULT now(),
    imgurl character varying,
    pimgurl character varying
);


ALTER TABLE public.replies OWNER TO postgres;

--
-- Name: replies_replyid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE replies_replyid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.replies_replyid_seq OWNER TO postgres;

--
-- Name: replies_replyid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE replies_replyid_seq OWNED BY replies.replyid;


--
-- Name: replyvotes; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE replyvotes (
    replyvoteid bigint NOT NULL,
    usr bigint,
    reply bigint,
    pointchange bigint
);


ALTER TABLE public.replyvotes OWNER TO postgres;

--
-- Name: replyvotes_replyvoteid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE replyvotes_replyvoteid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.replyvotes_replyvoteid_seq OWNER TO postgres;

--
-- Name: replyvotes_replyvoteid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE replyvotes_replyvoteid_seq OWNED BY replyvotes.replyvoteid;


--
-- Name: savedstories; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE savedstories (
    savedstoryid bigint NOT NULL,
    usr bigint,
    savedstory bigint
);


ALTER TABLE public.savedstories OWNER TO postgres;

--
-- Name: savedstories_savedstoryid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE savedstories_savedstoryid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.savedstories_savedstoryid_seq OWNER TO postgres;

--
-- Name: savedstories_savedstoryid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE savedstories_savedstoryid_seq OWNED BY savedstories.savedstoryid;


--
-- Name: stories; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE stories (
    usr bigint,
    storytime timestamp without time zone DEFAULT now(),
    title character varying,
    url character varying,
    text character varying,
    name character varying,
    score bigint DEFAULT 0,
    commentgroup bigint,
    storyid bigint NOT NULL,
    location bigint,
    imgurl character varying,
    pimgurl character varying,
    lastedit timestamp without time zone DEFAULT now(),
    channame character varying,
    id_from_feed character varying
);


ALTER TABLE public.stories OWNER TO postgres;

--
-- Name: stories_storyid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE stories_storyid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.stories_storyid_seq OWNER TO postgres;

--
-- Name: stories_storyid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE stories_storyid_seq OWNED BY stories.storyid;


--
-- Name: storygroup; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW storygroup AS
    SELECT stories.channame, stories.lastedit, stories.pimgurl, stories.imgurl, stories.usr, stories.storytime, stories.title, stories.url, stories.text, stories.name, stories.score, stories.commentgroup, stories.storyid, stories.location, commentgroups.commentgroupid, commentgroups.commentgrouptime, commentgroups.url AS recenttitle, commentgroups.cachedreplycount FROM (stories JOIN commentgroups ON ((stories.commentgroup = commentgroups.commentgroupid)));


ALTER TABLE public.storygroup OWNER TO postgres;

--
-- Name: storyvotes; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE storyvotes (
    usr bigint,
    story bigint,
    pointchange bigint,
    storyvoteid bigint NOT NULL
);


ALTER TABLE public.storyvotes OWNER TO postgres;

--
-- Name: storyvotes_storyvoteid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE storyvotes_storyvoteid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.storyvotes_storyvoteid_seq OWNER TO postgres;

--
-- Name: storyvotes_storyvoteid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE storyvotes_storyvoteid_seq OWNED BY storyvotes.storyvoteid;


--
-- Name: usrs; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE usrs (
    usrid bigint NOT NULL,
    name character varying,
    url character varying,
    email character varying,
    regtime timestamp without time zone DEFAULT now(),
    hometown character varying,
    state character varying,
    zip character varying,
    password character varying,
    postsperpage bigint DEFAULT 25,
    newmail bigint DEFAULT 0,
    status bigint DEFAULT 0,
    aboutme character varying,
    imgurl character varying,
    pimgurl character varying
);


ALTER TABLE public.usrs OWNER TO postgres;

--
-- Name: usrs_usrid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE usrs_usrid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.usrs_usrid_seq OWNER TO postgres;

--
-- Name: usrs_usrid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE usrs_usrid_seq OWNED BY usrs.usrid;


--
-- Name: usrsubs; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE usrsubs (
    usrsubid bigint NOT NULL,
    usr bigint,
    subbedchan bigint,
    subtime timestamp without time zone DEFAULT now()
);


ALTER TABLE public.usrsubs OWNER TO postgres;

--
-- Name: usrsubs_usrsubid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE usrsubs_usrsubid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.usrsubs_usrsubid_seq OWNER TO postgres;

--
-- Name: usrsubs_usrsubid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE usrsubs_usrsubid_seq OWNED BY usrsubs.usrsubid;


--
-- Name: chanid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE channels ALTER COLUMN chanid SET DEFAULT nextval('channels_chanid_seq'::regclass);


--
-- Name: commentgroupid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE commentgroups ALTER COLUMN commentgroupid SET DEFAULT nextval('commmentgroup_commentgroupid_seq'::regclass);


--
-- Name: feedid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE feeds ALTER COLUMN feedid SET DEFAULT nextval('feeds_feedid_seq'::regclass);


--
-- Name: msgid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE msgs ALTER COLUMN msgid SET DEFAULT nextval('msg_msgid_seq'::regclass);


--
-- Name: replyid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE replies ALTER COLUMN replyid SET DEFAULT nextval('replies_replyid_seq'::regclass);


--
-- Name: replyvoteid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE replyvotes ALTER COLUMN replyvoteid SET DEFAULT nextval('replyvotes_replyvoteid_seq'::regclass);


--
-- Name: savedstoryid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE savedstories ALTER COLUMN savedstoryid SET DEFAULT nextval('savedstories_savedstoryid_seq'::regclass);


--
-- Name: storyid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE stories ALTER COLUMN storyid SET DEFAULT nextval('stories_storyid_seq'::regclass);


--
-- Name: storyvoteid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE storyvotes ALTER COLUMN storyvoteid SET DEFAULT nextval('storyvotes_storyvoteid_seq'::regclass);


--
-- Name: usrid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE usrs ALTER COLUMN usrid SET DEFAULT nextval('usrs_usrid_seq'::regclass);


--
-- Name: usrsubid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE usrsubs ALTER COLUMN usrsubid SET DEFAULT nextval('usrsubs_usrsubid_seq'::regclass);


--
-- Name: commentgroup_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX commentgroup_idx ON stories USING btree (commentgroup);


--
-- Name: location_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX location_idx ON stories USING btree (location);


--
-- Name: storyid_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX storyid_idx ON stories USING btree (storyid);


--
-- Name: url_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX url_idx ON stories USING btree (url);


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- Name: chanclasses; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE chanclasses FROM PUBLIC;
REVOKE ALL ON TABLE chanclasses FROM postgres;
GRANT ALL ON TABLE chanclasses TO postgres;
GRANT ALL ON TABLE chanclasses TO lonuser;


--
-- Name: channels; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE channels FROM PUBLIC;
REVOKE ALL ON TABLE channels FROM postgres;
GRANT ALL ON TABLE channels TO postgres;
GRANT ALL ON TABLE channels TO lonuser;


--
-- Name: channels_chanid_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE channels_chanid_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE channels_chanid_seq FROM postgres;
GRANT ALL ON SEQUENCE channels_chanid_seq TO postgres;
GRANT ALL ON SEQUENCE channels_chanid_seq TO lonuser;


--
-- Name: commentgroups; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE commentgroups FROM PUBLIC;
REVOKE ALL ON TABLE commentgroups FROM postgres;
GRANT ALL ON TABLE commentgroups TO postgres;
GRANT ALL ON TABLE commentgroups TO lonuser;


--
-- Name: commmentgroup_commentgroupid_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE commmentgroup_commentgroupid_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE commmentgroup_commentgroupid_seq FROM postgres;
GRANT ALL ON SEQUENCE commmentgroup_commentgroupid_seq TO postgres;
GRANT ALL ON SEQUENCE commmentgroup_commentgroupid_seq TO lonuser;


--
-- Name: feeds; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE feeds FROM PUBLIC;
REVOKE ALL ON TABLE feeds FROM postgres;
GRANT ALL ON TABLE feeds TO postgres;
GRANT ALL ON TABLE feeds TO lonuser;


--
-- Name: feeds_feedid_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE feeds_feedid_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE feeds_feedid_seq FROM postgres;
GRANT ALL ON SEQUENCE feeds_feedid_seq TO postgres;
GRANT ALL ON SEQUENCE feeds_feedid_seq TO lonuser;


--
-- Name: msgs; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE msgs FROM PUBLIC;
REVOKE ALL ON TABLE msgs FROM postgres;
GRANT ALL ON TABLE msgs TO postgres;
GRANT ALL ON TABLE msgs TO lonuser;


--
-- Name: msg_msgid_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE msg_msgid_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE msg_msgid_seq FROM postgres;
GRANT ALL ON SEQUENCE msg_msgid_seq TO postgres;
GRANT ALL ON SEQUENCE msg_msgid_seq TO lonuser;


--
-- Name: replies; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE replies FROM PUBLIC;
REVOKE ALL ON TABLE replies FROM postgres;
GRANT ALL ON TABLE replies TO postgres;
GRANT ALL ON TABLE replies TO lonuser;


--
-- Name: replies_replyid_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE replies_replyid_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE replies_replyid_seq FROM postgres;
GRANT ALL ON SEQUENCE replies_replyid_seq TO postgres;
GRANT ALL ON SEQUENCE replies_replyid_seq TO lonuser;


--
-- Name: replyvotes; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE replyvotes FROM PUBLIC;
REVOKE ALL ON TABLE replyvotes FROM postgres;
GRANT ALL ON TABLE replyvotes TO postgres;
GRANT ALL ON TABLE replyvotes TO lonuser;


--
-- Name: replyvotes_replyvoteid_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE replyvotes_replyvoteid_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE replyvotes_replyvoteid_seq FROM postgres;
GRANT ALL ON SEQUENCE replyvotes_replyvoteid_seq TO postgres;
GRANT ALL ON SEQUENCE replyvotes_replyvoteid_seq TO lonuser;


--
-- Name: savedstories; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE savedstories FROM PUBLIC;
REVOKE ALL ON TABLE savedstories FROM postgres;
GRANT ALL ON TABLE savedstories TO postgres;
GRANT ALL ON TABLE savedstories TO lonuser;


--
-- Name: savedstories_savedstoryid_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE savedstories_savedstoryid_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE savedstories_savedstoryid_seq FROM postgres;
GRANT ALL ON SEQUENCE savedstories_savedstoryid_seq TO postgres;
GRANT ALL ON SEQUENCE savedstories_savedstoryid_seq TO lonuser;


--
-- Name: stories; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE stories FROM PUBLIC;
REVOKE ALL ON TABLE stories FROM postgres;
GRANT ALL ON TABLE stories TO postgres;
GRANT ALL ON TABLE stories TO lonuser;


--
-- Name: stories_storyid_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE stories_storyid_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE stories_storyid_seq FROM postgres;
GRANT ALL ON SEQUENCE stories_storyid_seq TO postgres;
GRANT ALL ON SEQUENCE stories_storyid_seq TO lonuser;


--
-- Name: storygroup; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE storygroup FROM PUBLIC;
REVOKE ALL ON TABLE storygroup FROM postgres;
GRANT ALL ON TABLE storygroup TO postgres;
GRANT ALL ON TABLE storygroup TO lonuser;


--
-- Name: storyvotes; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE storyvotes FROM PUBLIC;
REVOKE ALL ON TABLE storyvotes FROM postgres;
GRANT ALL ON TABLE storyvotes TO postgres;
GRANT ALL ON TABLE storyvotes TO lonuser;


--
-- Name: storyvotes_storyvoteid_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE storyvotes_storyvoteid_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE storyvotes_storyvoteid_seq FROM postgres;
GRANT ALL ON SEQUENCE storyvotes_storyvoteid_seq TO postgres;
GRANT ALL ON SEQUENCE storyvotes_storyvoteid_seq TO lonuser;


--
-- Name: usrs; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE usrs FROM PUBLIC;
REVOKE ALL ON TABLE usrs FROM postgres;
GRANT ALL ON TABLE usrs TO postgres;
GRANT ALL ON TABLE usrs TO lonuser;


--
-- Name: usrs_usrid_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE usrs_usrid_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE usrs_usrid_seq FROM postgres;
GRANT ALL ON SEQUENCE usrs_usrid_seq TO postgres;
GRANT ALL ON SEQUENCE usrs_usrid_seq TO lonuser;


--
-- Name: usrsubs; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE usrsubs FROM PUBLIC;
REVOKE ALL ON TABLE usrsubs FROM postgres;
GRANT ALL ON TABLE usrsubs TO postgres;
GRANT ALL ON TABLE usrsubs TO lonuser;


--
-- Name: usrsubs_usrsubid_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE usrsubs_usrsubid_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE usrsubs_usrsubid_seq FROM postgres;
GRANT ALL ON SEQUENCE usrsubs_usrsubid_seq TO postgres;
GRANT ALL ON SEQUENCE usrsubs_usrsubid_seq TO lonuser;


--
-- PostgreSQL database dump complete
--

