export interface RAGQueryHit {
  dish_name: string;
  ingredients: string[];
  cooking_method: string;
  cuisine: string;
  image_url: string;
  source_datasets: string[];
  cluster_id: string;
  score: number;
  directions: string[]; // Add directions field
}

export interface WebSource {
  title: string;
  link: string;
  snippet: string;
  displayLink: string;
  directions: string[]; // Add extracted directions
  content_preview: string; // Add content preview
  extraction_method?: 'llm' | 'simple' | 'error'; // Add extraction method
  recipe_info?: {
    // Add recipe info
    title?: string;
    description?: string;
    ingredients?: string[];
    instructions?: string[];
    cook_time?: string;
    prep_time?: string;
    total_time?: string;
  };
}

export interface RAGQueryResponse {
  query_ingredients: string[];
  hits: RAGQueryHit[];
  sources: Record<string, WebSource[]>; // Update to include WebSource type
}

export interface RAGQueryRequest {
  ingredients: string[];
  top?: number;
  mode?: 'flexible' | 'strict';
}
