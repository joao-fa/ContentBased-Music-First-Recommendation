

class DataframeClipping:
    def __init__(self, dataframe, test_df_percentage=20):
        self.dataframe = dataframe
        self.test_df_percentage = test_df_percentage
    
    def return_excat_row_by_percentage(self, percentage):
        return int(len(self.dataframe) * ((percentage) / 100))

    def clip_dataframe(self, num_rows, delimiter='end'):
        if delimiter == 'start':
            return self.dataframe.iloc[num_rows:].copy()
        elif delimiter == 'end':
            return self.dataframe.iloc[:num_rows].copy()
        else:
            raise Exception(f"Invalid given delimiter type {delimiter}. Try using 'start' or 'end'.") 

    def split_training_and_test_data(self):
        training_max_rows = self.return_excat_row_by_percentage(100 - self.test_df_percentage)
        training_subset =  self.clip_dataframe(training_max_rows, 'end')
        test_subset = self.clip_dataframe(training_max_rows, 'start')
        return training_subset, test_subset
    
    def preserve_dataframe_percentage(self, dataset_retention):
        if dataset_retention <= 0 or dataset_retention > 100:
            raise ValueError("The retention parameter of the dataset must be between 1 and 100.")
        num_rows_to_be_kept = self.return_excat_row_by_percentage(dataset_retention)
        return self.clip_dataframe(num_rows_to_be_kept)

        