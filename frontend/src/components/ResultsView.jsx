import React from 'react';
import styled, { keyframes } from 'styled-components';

/**
 * ResultsView - Three-Panel Layout for Query Results
 * 
 * Layout:
 * ┌────────────────┬─────────────────────────┬────────────────────┐
 * │   AUDIT LOG    │   KNOWLEDGE GRAPH       │    CITATIONS       │
 * │  (Cassandra)   │   (Reasoning Subgraph)  │  (PubMed/Trials)   │
 * └────────────────┴─────────────────────────┴────────────────────┘
 *                        [ Download PDF ]
 */

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
`;

const Container = styled.div`
  animation: ${fadeIn} 0.4s ease-out;
`;

const Header = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
`;

const Title = styled.h2`
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const QueryBadge = styled.span`
  font-size: 0.75rem;
  font-weight: 500;
  color: #64748b;
  background: #f1f5f9;
  padding: 0.25rem 0.75rem;
  border-radius: 99px;
`;

const DownloadButton = styled.button`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: linear-gradient(135deg, #059669 0%, #10b981 100%);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px -2px rgba(16, 185, 129, 0.4);

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px -2px rgba(16, 185, 129, 0.5);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  svg {
    width: 16px;
    height: 16px;
  }
`;

const PanelGrid = styled.div`
  display: grid;
  grid-template-columns: 280px 1fr 320px;
  gap: 1.25rem;
  min-height: 500px;

  @media (max-width: 1400px) {
    grid-template-columns: 1fr;
  }
`;

const Panel = styled.div`
  background: white;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
`;

const PanelHeader = styled.div`
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;

  h3 {
    font-size: 0.875rem;
    font-weight: 600;
    color: #334155;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  svg {
    width: 16px;
    height: 16px;
    color: #64748b;
  }
`;

const PanelContent = styled.div`
  flex: 1;
  padding: 1rem 1.25rem;
  overflow-y: auto;
`;

// Audit Panel Components
const AuditItem = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid #f1f5f9;

  &:last-child {
    border-bottom: none;
  }
`;

const StepIndicator = styled.div`
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: ${props => props.completed ? '#10b981' : '#e2e8f0'};
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 600;
  flex-shrink: 0;
`;

const StepInfo = styled.div`
  flex: 1;

  .name {
    font-size: 0.8rem;
    font-weight: 500;
    color: #0f172a;
  }

  .time {
    font-size: 0.7rem;
    color: #94a3b8;
    margin-top: 0.125rem;
  }
`;

const SafetyBadge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 8px;
  font-size: 0.75rem;
  font-weight: 600;
  background: ${props => 
    props.status === 'approved' ? '#d1fae5' :
    props.status === 'flagged' ? '#fef3c7' : '#fee2e2'};
  color: ${props =>
    props.status === 'approved' ? '#059669' :
    props.status === 'flagged' ? '#d97706' : '#dc2626'};
`;

// Graph Panel Components
const GraphContainer = styled.div`
  width: 100%;
  height: 350px;
  background: #f8fafc;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
`;

const GraphPlaceholder = styled.div`
  text-align: center;
  color: #64748b;

  svg {
    width: 48px;
    height: 48px;
    margin-bottom: 0.75rem;
    opacity: 0.5;
  }

  p {
    font-size: 0.875rem;
    margin: 0;
  }
`;

const NodeLegend = styled.div`
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
  flex-wrap: wrap;
`;

const LegendItem = styled.div`
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: #64748b;

  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: ${props => props.color};
  }
`;

// Citations Panel Components
const CitationCard = styled.div`
  padding: 0.875rem;
  background: #f8fafc;
  border-radius: 10px;
  margin-bottom: 0.75rem;

  &:last-child {
    margin-bottom: 0;
  }

  &:hover {
    background: #f1f5f9;
  }
`;

const CitationHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.5rem;
`;

const PMID = styled.a`
  font-size: 0.7rem;
  font-weight: 600;
  color: #2563eb;
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
`;

const ConfidenceBadge = styled.span`
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  background: ${props => props.high ? '#d1fae5' : props.medium ? '#fef3c7' : '#f1f5f9'};
  color: ${props => props.high ? '#059669' : props.medium ? '#d97706' : '#64748b'};
`;

const CitationTitle = styled.p`
  font-size: 0.8rem;
  font-weight: 500;
  color: #0f172a;
  margin: 0 0 0.375rem 0;
  line-height: 1.4;
`;

const CitationMeta = styled.div`
  font-size: 0.7rem;
  color: #94a3b8;
`;

// Simple SVG Graph Visualization
const SimpleGraph = ({ nodes, edges }) => {
  if (!nodes || nodes.length === 0) {
    return (
      <GraphPlaceholder>
        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        <p>No graph data available</p>
      </GraphPlaceholder>
    );
  }

  // Simple force-directed layout simulation
  const width = 400;
  const height = 300;
  const centerX = width / 2;
  const centerY = height / 2;

  // Position nodes in a circle
  const nodePositions = nodes.map((node, i) => {
    const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
    const radius = 100;
    return {
      ...node,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle)
    };
  });

  const nodeColors = {
    drug: '#3b82f6',
    target: '#8b5cf6',
    pathway: '#f59e0b',
    disease: '#ef4444',
    unknown: '#6b7280'
  };

  return (
    <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`}>
      {/* Edges */}
      {edges?.map((edge, i) => {
        const source = nodePositions.find(n => n.id === edge.source);
        const target = nodePositions.find(n => n.id === edge.target);
        if (!source || !target) return null;
        return (
          <g key={`edge-${i}`}>
            <line
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke="#cbd5e1"
              strokeWidth={Math.max(1, edge.confidence * 4)}
              markerEnd="url(#arrowhead)"
            />
            <text
              x={(source.x + target.x) / 2}
              y={(source.y + target.y) / 2 - 5}
              fontSize="8"
              fill="#64748b"
              textAnchor="middle"
            >
              {edge.relation}
            </text>
          </g>
        );
      })}
      
      {/* Arrow marker */}
      <defs>
        <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="#cbd5e1" />
        </marker>
      </defs>

      {/* Nodes */}
      {nodePositions.map((node, i) => (
        <g key={`node-${i}`}>
          <circle
            cx={node.x}
            cy={node.y}
            r={20}
            fill={nodeColors[node.node_type] || nodeColors.unknown}
            stroke="white"
            strokeWidth={2}
          />
          <text
            x={node.x}
            y={node.y + 35}
            fontSize="9"
            fill="#334155"
            textAnchor="middle"
            fontWeight="500"
          >
            {node.label?.length > 12 ? node.label.slice(0, 12) + '...' : node.label}
          </text>
        </g>
      ))}
    </svg>
  );
};

export default function ResultsView({ queryId, results, onDownloadPdf, isDownloading }) {
  // State for graph data from backend
  const [graphData, setGraphData] = React.useState({ nodes: [], edges: [] });
  const [graphLoading, setGraphLoading] = React.useState(false);

  // Extract data from results
  const auditSteps = results?.steps_completed || [];
  const safetyStatus = results?.approved ? 'approved' : 
                       results?.safety?.flags_count > 0 ? 'flagged' : 'approved';
  const candidates = results?.candidates || [];
  const evidence = results?.evidence_items || [];

  // Fetch graph data from backend API (source of truth)
  React.useEffect(() => {
    if (!queryId) return;
    
    const fetchGraph = async () => {
      setGraphLoading(true);
      try {
        // Use the backend graph endpoint
        const token = localStorage.getItem('biomind_access_token');
        const sessionId = localStorage.getItem('biomind_session_id');
        
        const response = await fetch(`http://10.20.72.65:8000/api/v1/reports/${queryId}/graph`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Session-ID': sessionId,
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          setGraphData({
            nodes: data.nodes || [],
            edges: data.edges || []
          });
        }
      } catch (err) {
        console.log('Graph fetch failed, using empty graph:', err);
      } finally {
        setGraphLoading(false);
      }
    };
    
    fetchGraph();
  }, [queryId]);

  // Use graph data from backend (validated, deduplicated, no stopwords)
  const graphNodes = graphData.nodes;
  const graphEdges = graphData.edges;

  return (
    <Container>
      <Header>
        <Title>
          <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Analysis Results
          <QueryBadge>{queryId}</QueryBadge>
        </Title>
        <DownloadButton onClick={onDownloadPdf} disabled={isDownloading}>
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          {isDownloading ? 'Generating...' : 'Download PDF'}
        </DownloadButton>
      </Header>

      <PanelGrid>
        {/* LEFT: Audit Panel */}
        <Panel>
          <PanelHeader>
            <h3>
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Audit Trail
            </h3>
          </PanelHeader>
          <PanelContent>
            <SafetyBadge status={safetyStatus}>
              {safetyStatus === 'approved' && '✓ Safety Approved'}
              {safetyStatus === 'flagged' && '⚠ Flagged for Review'}
              {safetyStatus === 'blocked' && '✕ Blocked'}
            </SafetyBadge>
            
            <div style={{ marginTop: '1rem' }}>
              {auditSteps.map((step, i) => (
                <AuditItem key={i}>
                  <StepIndicator completed>{i + 1}</StepIndicator>
                  <StepInfo>
                    <div className="name">{step.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                    <div className="time">Completed</div>
                  </StepInfo>
                </AuditItem>
              ))}
              {auditSteps.length === 0 && (
                <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>No audit steps recorded</p>
              )}
            </div>
          </PanelContent>
        </Panel>

        {/* CENTER: Graph Panel */}
        <Panel>
          <PanelHeader>
            <h3>
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Reasoning Subgraph
            </h3>
          </PanelHeader>
          <PanelContent>
            <GraphContainer>
              <SimpleGraph nodes={graphNodes} edges={graphEdges} />
            </GraphContainer>
            <NodeLegend>
              <LegendItem color="#3b82f6"><span className="dot" /> Drug</LegendItem>
              <LegendItem color="#8b5cf6"><span className="dot" /> Target</LegendItem>
              <LegendItem color="#f59e0b"><span className="dot" /> Pathway</LegendItem>
              <LegendItem color="#ef4444"><span className="dot" /> Disease</LegendItem>
            </NodeLegend>

            {/* Candidates Summary */}
            {candidates.length > 0 && (
              <div style={{ marginTop: '1rem', padding: '0.75rem', background: '#f0fdf4', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: '600', color: '#059669' }}>
                  {candidates.length} Candidate{candidates.length !== 1 ? 's' : ''} Identified
                </div>
                <div style={{ fontSize: '0.75rem', color: '#047857', marginTop: '0.25rem' }}>
                  Top: {candidates[0]?.drug_name} → {candidates[0]?.target_disease}
                </div>
              </div>
            )}
          </PanelContent>
        </Panel>

        {/* RIGHT: Citations Panel */}
        <Panel>
          <PanelHeader>
            <h3>
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              Citations ({evidence.length})
            </h3>
          </PanelHeader>
          <PanelContent>
            {evidence.length === 0 ? (
              <p style={{ color: '#94a3b8', fontSize: '0.8rem', textAlign: 'center', padding: '2rem 0' }}>
                No citations available
              </p>
            ) : (
              evidence.slice(0, 10).map((ev, i) => (
                <CitationCard key={i}>
                  <CitationHeader>
                    <PMID href={`https://pubmed.ncbi.nlm.nih.gov/${ev.source || ''}`} target="_blank" rel="noopener noreferrer">
                      PMID: {ev.source || 'N/A'}
                    </PMID>
                    <ConfidenceBadge 
                      high={ev.confidence >= 0.7}
                      medium={ev.confidence >= 0.4 && ev.confidence < 0.7}
                    >
                      {Math.round((ev.confidence || 0) * 100)}%
                    </ConfidenceBadge>
                  </CitationHeader>
                  <CitationTitle>{ev.description?.slice(0, 100) || 'No title'}...</CitationTitle>
                  <CitationMeta>{ev.evidence_type}</CitationMeta>
                </CitationCard>
              ))
            )}
          </PanelContent>
        </Panel>
      </PanelGrid>
    </Container>
  );
}
