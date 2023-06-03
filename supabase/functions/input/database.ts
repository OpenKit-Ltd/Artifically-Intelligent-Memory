import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";
import { OpenAIEmbeddings } from "langchain/embeddings/openai";
import { Document } from "langchain/document";


const embeddings = new OpenAIEmbeddings({openai_api_key: Deno.env.get('OPENAI_API_KEY')});



export const insertSensoryInput = async (supabaseClient: any, source: string) => {
  console.log("Inserting sensory input")
  console.log("source", source)
  try {

    const { data, error } = await supabaseClient.from('sensory_inputs').insert({ source, creation_date: new Date() }).select();

    if (error) throw error;
    console.log("data", data)
    return data[0].input_id;
  } catch (error) {
    console.error(error);
    return -1;
  }
}



export const insertInputChunks = async (supabaseClient: any, inputId: number, inputChunkDocuments: Document[])  => {
  console.log("Inserting input chunks")
  console.log("inputId", inputId)
  console.log("chunks", inputChunkDocuments)
  try {
    const inputChunks = inputChunkDocuments.map(async (inputChunk, index) => {
      const {content, metadata} = inputChunk
      const embedding = await embeddings.embedQuery(content);
      return {
        input_id: inputId,
        content,
        metadata,
        embedding,
        sequence_number: index,
      }
    });
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