-- roles table
CREATE TABLE roles (
	id SERIAL NOT NULL,
	name VARCHAR (250) NOT NULL,
	description VARCHAR (500) NULL,
	start VARCHAR (250) NULL,
	CONSTRAINT pk_roles
	PRIMARY KEY( id )
);