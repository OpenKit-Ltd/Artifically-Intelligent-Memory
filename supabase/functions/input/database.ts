import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";
import { OpenAIEmbeddings } from "langchain/embeddings/openai";

const embeddings = new OpenAIEmbeddings({openai_api_key: Deno.env.get('SUPABASE_URL')});



export const insertSensoryInput = async (supabaseClient: any, source: string) => {
  try {
    const { data, error } = await supabaseClient.from('sensory_inputs').insert({ source, creation_date: new Date() });
    if (error) throw error;
    return data[0].input_id;
  } catch (error) {
    console.error(error);
    return -1;
  }
}



export const insertInputChunks = async (supabaseClient: any, inputId: number, chunks: string[])  => {
  try {
    const inputChunks = chunks.map((content, index) => ({
      input_id: inputId,
      content,
      embedding: null, // Replace with the actual embedding vector
      sequence_number: index,
    }));

    const { error } = await supabaseClient.from('input_chunks').insert(inputChunks);
    if (error) throw error;
  } catch (error) {
    console.error(error);
  }
}


export const handleSensoryInput = async (supabaseClient: any, raw_text: string, source: string) => {
    const splitter = new RecursiveCharacterTextSplitter({
        chunkSize: 1000,
        chunkOverlap: 250,
    });

    const output = await splitter.createDocuments([raw_text]);
    const inputId = await insertSensoryInput(supabaseClient, source);
    if (inputId !== -1) {
        await insertInputChunks(supabaseClient, inputId, output);
    }
}