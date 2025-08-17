# Recipe Finder (RAG Query) Feature

This feature allows users to find recipes based on available ingredients using a RAG (Retrieval-Augmented Generation) system.

## Features

- **Ingredient Input**: Users can add multiple ingredients they have available
- **Recipe Search**: Finds matching recipes from the database based on ingredient similarity
- **Recipe Cards**: Displays recipes with:
  - Dish name
  - Required ingredients
  - Cooking method
  - Cuisine type
  - Recipe image (if available)
  - Source dataset information
  - Match score percentage

## Components

### Main Components

- `RagQueryComponent`: Main page component with navigation
- `RagQueryInputComponent`: Handles ingredient input and submission
- `RagQueryResultsComponent`: Displays search results in card format

### Models

- `RAGQueryResponse`: Response structure from the backend
- `RAGQueryHit`: Individual recipe result
- `RAGQueryRequest`: Request structure for the API

### Services

- `ApiService.queryRAG()`: Makes HTTP requests to the backend query endpoint

## Backend Integration

The frontend communicates with the Flask backend via:

- `GET /query?i=ingredient1,ingredient2&top=5`

## Usage

1. Navigate to the "Recipe Finder" page
2. Add ingredients you have available by typing and pressing Enter or clicking "Add"
3. Click "Find Recipes" to search
4. Browse through the matching recipes displayed in cards
5. Each card shows the match percentage, ingredients, cooking method, and other details

## Styling

The components use modern CSS with:

- Responsive grid layout for recipe cards
- Color-coded match scores (green for high, yellow for medium, red for low)
- Hover effects and smooth transitions
- Mobile-friendly design

## Navigation

The app now has two main pages:

- **Food Analyzer**: Original image analysis functionality
- **Recipe Finder**: New RAG-based recipe search functionality

Users can switch between pages using the navigation bar at the top of each page.

