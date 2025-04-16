# GBC Course Catalog Frontend

A modern web interface for browsing GBC continuing education courses.

## Features

- Course search and filtering
- Dark mode support
- Responsive design
- Real-time filtering by:
  - Department
  - Day of week
  - Time of day
  - Delivery type (Online/On Campus)

## Getting Started

### Prerequisites

- Node.js 18+
- npm

### Installation

```bash
npm install
```

### Development

The application can run in two modes:

1. Test Mode (using mock data):

    ```bash
    npm run dev:test
    ```

2. Production Mode (using API):

  ```bash
  npm run dev:prod
  ```

1. Or use the default development command:

  ```bash
  npm run dev
  ```

### Environment Variables

Create a `.env.local` file:

```text
NEXT_PUBLIC_USE_TEST_DATA=true  # Set to false for production data
```

### Building for Production

```bash
npm run build
npm run start
```

## Project Structure

```bash
src/
  ├── api/          # API client and endpoints
  ├── components/   # React components
  ├── hooks/        # Custom React hooks
  ├── pages/        # Next.js pages
  ├── types/        # TypeScript type definitions
  └── utils/        # Utility functions and test data
```

## Testing

The application includes a test data mode that can be used without the backend API. This is useful for development and testing UI changes.

## Tech Stack

- Next.js
- React
- TypeScript
- Tailwind CSS
- React Query
- Axios
