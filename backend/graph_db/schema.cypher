// BioMind Nexus - Neo4j Graph Schema
//
// Defines the knowledge graph schema for biomedical entities and relationships.
// Run this script to initialize a fresh Neo4j database.
//
// Schema follows the Biolink Model for interoperability.
// All nodes have: id (unique), name, created_at, updated_at
// All relationships have: source, confidence, created_at

// ============================================================================
// Constraints (enforce uniqueness and existence)
// ============================================================================

CREATE CONSTRAINT gene_id IF NOT EXISTS FOR (g:Gene) REQUIRE g.id IS UNIQUE;
CREATE CONSTRAINT disease_id IF NOT EXISTS FOR (d:Disease) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT drug_id IF NOT EXISTS FOR (dr:Drug) REQUIRE dr.id IS UNIQUE;
CREATE CONSTRAINT pathway_id IF NOT EXISTS FOR (p:Pathway) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT publication_id IF NOT EXISTS FOR (pub:Publication) REQUIRE pub.id IS UNIQUE;

// ============================================================================
// Indexes (optimize query performance)
// ============================================================================

CREATE INDEX gene_name IF NOT EXISTS FOR (g:Gene) ON (g.name);
CREATE INDEX disease_name IF NOT EXISTS FOR (d:Disease) ON (d.name);
CREATE INDEX drug_name IF NOT EXISTS FOR (dr:Drug) ON (dr.name);
CREATE INDEX publication_pmid IF NOT EXISTS FOR (pub:Publication) ON (pub.pmid);

// ============================================================================
// Node Labels and Properties
// ============================================================================

// Gene/Protein node
// Properties: id, symbol, name, description, organism, entrez_id, ensembl_id

// Disease node
// Properties: id, name, description, doid, mesh_id, icd10

// Drug/Compound node
// Properties: id, name, description, drugbank_id, chembl_id, smiles

// Pathway node
// Properties: id, name, description, source (kegg, reactome, go)

// Publication node
// Properties: id, pmid, doi, title, abstract, authors, year, journal

// ============================================================================
// Relationship Types
// ============================================================================

// Gene-Gene relationships
// (g1:Gene)-[:INTERACTS_WITH {score, source}]->(g2:Gene)
// (g1:Gene)-[:REGULATES {direction, mechanism}]->(g2:Gene)

// Gene-Disease relationships
// (g:Gene)-[:ASSOCIATED_WITH {score, source, evidence_type}]->(d:Disease)
// (g:Gene)-[:CAUSES {mechanism}]->(d:Disease)

// Drug-Gene relationships
// (dr:Drug)-[:TARGETS {action, score}]->(g:Gene)

// Drug-Disease relationships
// (dr:Drug)-[:TREATS {phase, approval_status}]->(d:Disease)

// Pathway relationships
// (g:Gene)-[:PARTICIPATES_IN]->(p:Pathway)
// (p1:Pathway)-[:UPSTREAM_OF]->(p2:Pathway)

// Publication relationships
// (pub:Publication)-[:MENTIONS {context}]->(entity)
// (pub:Publication)-[:SUPPORTS {statement}]->(relationship)
