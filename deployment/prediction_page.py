import pandas as pd
import numpy as np
import pickle
import json
import streamlit as st
import numpy as np
import spacy
from spacy.matcher import DependencyMatcher
from sklearn.preprocessing import Normalizer

nlp = spacy.load('en_core_web_lg')
matcher = DependencyMatcher(nlp.vocab)

# Open the pattern JSON file
with open("patterns.json", "r") as file:
    patterns_dict = json.load(file)

# Add the patterns to the matcher
for pattern_name, pattern_list in patterns_dict.items():
    matcher.add(f'{pattern_name}', [pattern_list])

def load_model():
    with open('random_forest_smote_67.pkl', 'rb') as file:
        loaded_model = pickle.load(file)
    return loaded_model

model = load_model()

def count_patterns(text, matcher):
    """Count the number of pattern matches in the text."""
    doc = nlp(text)
    matches = matcher(doc)
    counts = {pattern_name: 0 for pattern_name in patterns_dict.keys()}
    for match_id, token_ids in matches:
        pattern_name = matcher.vocab.strings[match_id]
        counts[pattern_name] += 1
    return counts

def preprocess_text(doc):
    """Remove stop words, punctuation, nouns, lemmatize the text, and return the document vector."""
    # Remove stop words, punctuation, and nouns, and lemmatize
    tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
    # Join the tokens back to a single string (if needed)
    preprocessed_text = ' '.join(tokens)
    # Return the document vector
    vector = doc.vector
    return preprocessed_text, vector

def find_patterns(df):
    df = df.copy()
    pattern_names = list(patterns_dict.keys())
    
    # Initialize columns for pattern counts as floats
    for pattern_name in pattern_names:
        df[pattern_name] = 0.0
    
    df['num_sentences'] = 0
    df['avg_sentence_len'] = 0.0
    df['preprocessed_text'] = ""
    df['doc_vector'] = None
    
    for index, row in df.iterrows():
        answer_text = row['answer']
        doc = nlp(answer_text)
        total_tokens = 0
        num_sentences = 0

        # First, count the sentences and calculate average sentence length
        for sentence in doc.sents:
            num_tokens = len(sentence)
            total_tokens += num_tokens
            num_sentences += 1

        avg_sentence_len = total_tokens / num_sentences if num_sentences > 0 else 0
        df.loc[index, 'num_sentences'] = num_sentences
        df.loc[index, 'avg_sentence_len'] = avg_sentence_len

        # Count patterns in the original text
        pattern_counts = count_patterns(answer_text, matcher)
        for pattern_name, count in pattern_counts.items():
            df.at[index, pattern_name] = count / num_sentences if num_sentences > 0 else 0
        
        # Then preprocess the text
        preprocessed_text, vector = preprocess_text(doc)
        df.at[index, 'preprocessed_text'] = preprocessed_text
        df.at[index, 'doc_vector'] = vector
    
    print(df)
    return df

def show_predict_page():
    st.title("ESL Writing Classification")
    st.write(""" ### Provide the following info""")
    text = st.text_area("Input text here")
    submit = st.button("Submit")

    if submit:
        df = pd.DataFrame({'answer': [text]})
        df = find_patterns(df)
        df = df.reset_index(drop=True)
        doc_vectors_df = pd.DataFrame(df['doc_vector'].values.tolist(), columns=[f'doc_vector_{i}' for i in range(300)])
        doc_vectors_df = doc_vectors_df.reset_index(drop=True)
        df_concat = pd.concat([df, doc_vectors_df], axis=1)
        X = df_concat.drop(['answer', 'preprocessed_text', 'doc_vector'],axis=1)
        normalizer = Normalizer()
        X = normalizer.transform(X)
        predicted_class = model.predict(X)
        st.markdown(f"""
            <div style='background-color: #f0f0f0; padding: 10px; border-radius: 5px'>
                <table style='width: 80%; border-collapse: collapse;'>
                    <tr>
                    <th>Predicted Class:</th>
                    <th>{predicted_class}</th>
                    </tr>
                    <tr>
                        <td>Number of sentences:</td>
                        <td>{df['num_sentences'].iloc[0]}</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)