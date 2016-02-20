import json
import numpy

import next.apps.SimpleTargetManager
import next.utils as utils
class CardinalBanditsPureExploration(object):
    def __init__(self):
        self.app_id = 'CardinalBanditsPureExploration'
        self.TargetManager = next.apps.SimpleTargetManager.SimpleTargetManager()

    def initExp(self, exp_uid, exp_data, butler):
        """
        This function is meant to store any additional components in the
        databse.

        Inputs
        ------
        exp_uid : The unique identifier to represent an experiment.
        exp_data : The keys specified in the app specific YAML file in the
                   initExp section.
        butler : The wrapper for database writes. See next/apps/Butler.py for
                 more documentation.

        Returns
        -------
        exp_data: The experiment data, potentially modified.
        """
        if 'targetset' in exp_data['args']['targets'].keys():
            n  = len(exp_data['args']['targets']['targetset'])
            self.TargetManager.set_targetset(exp_data['args']['targets']['targetset'])
        else:
            n = exp_data['args']['targets']['n']
        exp_data['args']['n'] = n
        del exp_data['args']['targets']

        if 'labels' in exp_data['args']['rating_scale'].keys():
            max_label = max( label['reward'] for label in labels )
            min_label = min( label['reward'] for label in labels )
            exp_data['args']['rating_scale']['R'] = max_label-min_label
        return exp_data

    def getQuery(self, exp_uid, query_request, alg_response, butler):
        """
        The function that gets the next query, given a query reguest and
        algorithm response.

        Inputs
        ------
        exp_uid : The unique identiefief for the exp.
        query_request :
        alg_response : The response from the algorithm. The algorithm should
                       return only one value, be it a list or a dictionary.
        butler : The wrapper for database writes. See next/apps/Butler.py for
                 more documentation.

        Returns
        -------
        A dictionary with a key ``target_indices``.

        TODO: Document this further
        """
        target = self.TargetManager.get_target_item(exp_uid, alg_response)

        targets_list = [{'target':target}]

        return {'target_indices':targets_list}

    def processAnswer(self, exp_uid, query, answer, butler):
        """
        Parameters
        ----------
        exp_uid : The experiments unique ID.
        query :
        answer: 
        butler : 

        Returns
        -------
        dictionary with keys:
            alg_args: Keywords that are passed to the algorithm.
            query_update :

        For example, this function might return ``{'a':1, 'b':2}``. The
        algorithm would then be called with
        ``alg.processAnswer(butler, a=1, b=2)``
        """
        target_id = query['target_indices'][0]['target']['target_id']     
        target_reward = answer['args']['target_reward']
        butler.experiment.increment(key='num_reported_answers_for_' + query['alg_label'])
        return {'alg_args':{'left_id':left_id, 
                            'right_id':right_id, 
                            'winner_id':winner_id,
                            'painted_id':painted_id},
                'query_update':{'winner_id':winner_id}}

    def getModel(self, exp_uid, alg_response, args_dict, butler):
        scores, precisions = alg_response
        ranks = (-numpy.array(scores)).argsort().tolist()
        n = len(scores)
        indexes = numpy.array(range(n))[ranks]
        scores = numpy.array(scores)[ranks]
        precisions = numpy.array(precisions)[ranks]
        ranks = range(n)

        targets = []
        for index in range(n):
          targets.append( {'index':indexes[index],
                           'target':self.TargetManager.get_target_item(exp_uid, indexes[index]),
                           'rank':ranks[index],
                           'score':scores[index],
                           'precision':precisions[index]} )
        num_reported_answers = butler.experiment.get('num_reported_answers')
        return {'targets': targets, 'num_reported_answers':num_reported_answers} 
        
    def getStats(self, exp_uid, stats_request, dashboard, butler):
        """
        Get statistics to display on the dashboard.
        """
        stat_id = stats_request['args']['stat_id']
        task = stats_request['args']['params'].get('task', None)
        alg_label = stats_request['args']['params'].get('alg_label', None)
        functions = {'api_activity_histogram':dashboard.api_activity_histogram,
                     'compute_duration_multiline_plot':dashboard.compute_duration_multiline_plot,
                     'compute_duration_detailed_stacked_area_plot':dashboard.compute_duration_detailed_stacked_area_plot,
                     'response_time_histogram':dashboard.response_time_histogram,
                     'network_delay_histogram':dashboard.network_delay_histogram,
                     'most_current_ranking':dashboard.most_current_ranking}

        default = [self.app_id, exp_uid]
        args = {'api_activity_histogram':default + [task],
                'compute_duration_multiline_plot':default + [task],
                'compute_duration_detailed_stacked_area_plot':default + [task, alg_label],
                'response_time_histogram':default + [alg_label],
                'network_delay_histogram':default + [alg_label],
                'most_current_ranking':default + [alg_label]}
        return functions[stat_id](*args[stat_id])
