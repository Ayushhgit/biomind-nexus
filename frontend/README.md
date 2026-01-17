# BioMind Nexus - Frontend

React.js frontend for the BioMind Nexus research assistant.

## Development Setup

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

## Structure

- `src/pages/` - Page components (routing handled by React Router)
- `src/components/` - Reusable React components
- `src/services/` - API client and service layer

## API Integration

All backend communication goes through the `services/api.ts` client.
Authentication tokens are stored in memory (not localStorage) for security.

## Tech Stack

- React 18 with TypeScript
- Vite for bundling
- React Router for routing
