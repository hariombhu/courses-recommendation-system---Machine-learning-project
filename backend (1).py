import pandas as pd
import numpy as np

import pandas as pd
import numpy as np


from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA


models = ("Course Similarity",
          "User Profile",
          "Clustering",
        
        )


def load_ratings():
    return pd.read_csv("ratings.csv")


def load_course_sims():
    return pd.read_csv("sim.csv")


def load_courses():
    df = pd.read_csv("course_processed.csv")
    df['TITLE'] = df['TITLE'].str.title()
    return df


def load_profile():
    return pd.read_csv("user_profile.csv")
    
def load_courses_genre():
    return pd.read_csv("course_genre.csv")


def load_bow():
    return pd.read_csv("courses_bows.csv")


def add_new_ratings(new_courses):
    res_dict = {}
    if len(new_courses) > 0:
        
        ratings_df = load_ratings()
        new_id = ratings_df['user'].max() + 1
        users = [new_id] * len(new_courses)
        ratings = [3.0] * len(new_courses)
        res_dict['user'] = users
        res_dict['item'] = new_courses
        res_dict['rating'] = ratings
        new_df = pd.DataFrame(res_dict)
        updated_ratings = pd.concat([ratings_df, new_df])
        updated_ratings.to_csv("ratings.csv", index=False)
        return new_id



def get_doc_dicts():
    bow_df = load_bow()
    grouped_df = bow_df.groupby(['doc_index', 'doc_id']).max().reset_index(drop=False)
    idx_id_dict = grouped_df[['doc_id']].to_dict()['doc_id']
    id_idx_dict = {v: k for k, v in idx_id_dict.items()}
    del grouped_df
    return idx_id_dict, id_idx_dict


def course_similarity_recommendations(idx_id_dict, id_idx_dict, enrolled_course_ids, sim_matrix):
    all_courses = set(idx_id_dict.values())
    unselected_course_ids = all_courses.difference(enrolled_course_ids)
    
    res = {}
    
    for enrolled_course in enrolled_course_ids:
        for unselect_course in unselected_course_ids:
            if enrolled_course in id_idx_dict and unselect_course in id_idx_dict:
                idx1 = id_idx_dict[enrolled_course]
                idx2 = id_idx_dict[unselect_course]
                sim = sim_matrix[idx1][idx2]
                if unselect_course not in res:
                    res[unselect_course] = sim
                else:
                    if sim >= res[unselect_course]:
                        res[unselect_course] = sim
    res = {k: v for k, v in sorted(res.items(), key=lambda item: item[1], reverse=True)}
    return res



def train(model_name, params):
    # TODO: Add model training code here
    if "cluster_no" in params:
        cluster_no = params["cluster_no"]

    if model_name == models[2]:
        user_profile_df = load_profile()
        scaler = StandardScaler()
        
        feature_names = list(user_profile_df.columns[1:])
        features = user_profile_df.loc[:, user_profile_df.columns != 'user']

        user_profile_df[feature_names] = scaler.fit_transform(user_profile_df[feature_names])
        user_ids = user_profile_df.loc[:, user_profile_df.columns == 'user']

        km = KMeans(n_clusters=cluster_no, random_state=42)
        km = km.fit(features)
        cluster_labels = km.labels_
        res_df = combine_cluster_labels(user_ids,labels=cluster_labels)
        return res_df
        


    

    


def combine_cluster_labels(user_ids, labels):
    labels_df = pd.DataFrame(labels)
    cluster_df = pd.merge(user_ids, labels_df, left_index=True, right_index=True)
    cluster_df.columns = ['user', 'cluster']
    return cluster_df



def predict(model_name, user_ids, params):
    sim_threshold = 0.6
    profile_sim_threshold = 10.0
    
    idx_id_dict, id_idx_dict = get_doc_dicts()
    sim_matrix = load_course_sims().to_numpy()
    users = []
    courses = []
   
    scores = []
    res_dict = {}
    if "profile_sim_threshold" in params:
        profile_sim_threshold = params["profile_sim_threshold"]
    
    elif "sim_threshold" in params:
        sim_threshold = params["sim_threshold"] / 100.0
    elif "cluster_no" in params:
        cluster_no = params["cluster_no"]
        temp_user_two = params["temp_user_two"]
        temp_user_two = int(temp_user_two)
    else:
        pass


    for user_id in user_ids:
        # Course Similarity model
        if model_name == models[0]:
            ratings_df = load_ratings()
            user_ratings = ratings_df[ratings_df['user'] == user_id]
            enrolled_course_ids = user_ratings['item'].to_list()
            res = course_similarity_recommendations(idx_id_dict, id_idx_dict, enrolled_course_ids, sim_matrix)
            for key, score in res.items():
                if score >= sim_threshold:
                    users.append(user_id)
                    courses.append(key)
                    scores.append(score)
            res_dict['USER'] = users
            res_dict['COURSE_ID'] = courses
            res_dict['SCORE'] = scores
            res_df = pd.DataFrame(res_dict, columns=['USER', 'COURSE_ID', 'SCORE'])
        else:
            break
        # TODO: Add prediction model code here
    if model_name == models[1]:

        if "user_id" in params:
            temp_user = params['user_id']
            temp_user = int(temp_user)
        else:
            pass

        ratings_df = load_ratings()
        profile_df =load_profile()
        course_genres_df =load_courses_genre()
        all_courses = set(course_genres_df['COURSE_ID'].values)
        test_user_profile = profile_df[profile_df['user'] == temp_user]
       
        test_user_vector = test_user_profile.iloc[0, 1:].values
        
        
        enrolled_courses = ratings_df[ratings_df['user'] == temp_user]['item'].to_list()
        unknown_courses = all_courses.difference(enrolled_courses)
        unknown_course_df = course_genres_df[course_genres_df['COURSE_ID'].isin(unknown_courses)]
        unknown_course_ids = unknown_course_df['COURSE_ID'].values
        course_matrix = unknown_course_df.iloc[:, 2:].values
        
        recommendation_scores = np.dot(course_matrix,test_user_vector)
        for i in range(0, len(unknown_course_ids)):
            score = recommendation_scores[i]
            
            if score >= profile_sim_threshold:
                
                courses.append(unknown_course_ids[i])
                scores.append(recommendation_scores[i])
        
        res_dict['COURSE_ID'] = courses
        res_dict['SCORE'] = scores
        res_df = pd.DataFrame(res_dict, columns=['COURSE_ID', 'SCORE'])
    

    if model_name == models[2]:
        
        
        res_df=train(model_name, params)
        
        filt = res_df['user']== temp_user_two
        cluster_value  = int(res_df[filt]['cluster'])
        filt2 = res_df['cluster'] == cluster_value
        res_df =res_df[filt2]
        
        




    return res_df
