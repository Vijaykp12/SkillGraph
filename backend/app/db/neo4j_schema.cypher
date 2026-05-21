// Neo4j Database Schema constraints and indices for SkillGraph

CREATE CONSTRAINT unique_skill_id IF NOT EXISTS
FOR (s:Skill) REQUIRE s.id IS UNIQUE;

CREATE INDEX skill_name_idx IF NOT EXISTS
FOR (s:Skill) ON (s.name);

CREATE CONSTRAINT unique_occupation_id IF NOT EXISTS
FOR (o:Occupation) REQUIRE o.id IS UNIQUE;

CREATE INDEX occupation_name_idx IF NOT EXISTS
FOR (o:Occupation) ON (o.name);

CREATE CONSTRAINT unique_company_id IF NOT EXISTS
FOR (c:Company) REQUIRE c.id IS UNIQUE;

CREATE INDEX company_name_idx IF NOT EXISTS
FOR (c:Company) ON (c.name);

CREATE CONSTRAINT unique_resource_id IF NOT EXISTS
FOR (r:LearningResource) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT unique_certification_id IF NOT EXISTS
FOR (cert:Certification) REQUIRE cert.id IS UNIQUE;

CREATE CONSTRAINT unique_technology_id IF NOT EXISTS
FOR (t:Technology) REQUIRE t.id IS UNIQUE;
