CREATE TABLE public.base_conhecimento (
	id int GENERATED ALWAYS AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	titulo varchar(255) NOT NULL,
	conteudo text NOT NULL,
	data_criacao timestamp NULL,
	CONSTRAINT base_conhecimento_pk PRIMARY KEY (id)
);