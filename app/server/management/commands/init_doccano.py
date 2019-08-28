from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from rest_framework.reverse import reverse
from rest_framework.authtoken.models import Token


from api.models import Project, Label, Document, SequenceLabelingProject

import requests
import json
import random
import os

class Command(BaseCommand):
    help = 'Initialization. create a project for each user'

    def add_arguments(self, parser):
        # parser.add_argument('admin_id', nargs=1, type=int)
        parser.add_argument('users_list', nargs=1, type=str)
        parser.add_argument('path_annotation_file', nargs=1, type=str)

    def handle(self, *args, **options):
        admin = User.objects.get(username='admin')
        # admin_id = options['admin_id'][0]
        admin_id = admin.id

        admin_token, created = Token.objects.get_or_create(user=admin)
        print(admin_token.key)

        users_list = []

        if options['users_list'][0].endswith('.json'):
            with open(options['users_list'][0]) as data_file:
                users_list = json.load(data_file)
            # users_list = json.loads()
        else:
            print("input file must be json file (.json)")
            exit()
        # users_list = [
        #     {'name': 'john', 'email': 'lennon@thebeatles.com', 'password': 'johnpassword'},
        #     {'name': 'other', 'email': 'other@thebeatles.com', 'password': 'otherpassword'}
        # ]


        annotation_files = os.listdir(options['path_annotation_file'][0])
        print(annotation_files)
        # Project definition
        description = "The aim here is to check if the annotations are correct and to modify them if necessary (e.g., class modification), " \
                      "remove the wrong ones and to add new ones if they were forgotten. "
        guideline = "Interactions: \n" \
                    "- Add annotation: select the named entity and click on the right class among classes displayed above (then it should be highlighted) \n" \
                    "- Remove annotation: click on the cross at the end of the named entity \n" \
                    "- Modify class: remove the annotation and add a new one with the right class \n" \
                    "⚠ Once you remove an annotation you cannot go back (i.e., no crtl-z)"

        for i, u in enumerate(users_list):
            # Create users with superuser rights
            user = User.objects.create_user(u['name'], u['email'], u['password'], is_superuser=False)
            user.save()
            u['id'] = User.objects.get(username=u['name']).id
            users_list[i] = u
            print(id)

            #Project creation
            project_name = "Named entity recognition - " + u['name']
            # project = Project.objects.create(name=project_name, description=description, guideline=guideline,
            #                          project_type='SequenceLabeling', randomize_document_order=False,
            #                          collaborative_annotation=True)
            # project.users.add(u['id'])
            # project.users.add(admin_id)

            seq_project = SequenceLabelingProject.objects.create()
            seq_project.name = project_name
            seq_project.description = description
            seq_project.guideline = guideline
            seq_project.project_type = 'SequenceLabeling'
            seq_project.randomize_document_order = False
            seq_project.collaborative_annotation = True
            seq_project.users.add(u['id'])
            seq_project.users.add(admin_id)
            seq_project.save()

            project_id = Project.objects.get(name=project_name).id
            print(project_id)

            headers = {
                'Authorization': 'Token ' + admin_token.key
            }

            # Import labels
            labels_list = self.get_labels()
            # labels = []
            for l in labels_list:
                # labels.append(json.loads(json.dumps({"text": l})))
                color = "%06x" % random.randint(0, 0xFFFFFF)
                data = {
                    'text': l.upper(),
                    'background_color': '#'+ color,
                    'text_color': '#000000'
                }
                post = requests.post(url='http://127.0.0.1:8888' + reverse(viewname='label_list', args=[project_id]),
                                     headers=headers, data=data)

            # labels = json.dumps(labels)
            # print(labels)


            # Import sentences
            data = {
                'format': 'json'
            }

            # files = {'file': open('/sharedWindows/tmpAnnotation_small.txt', 'rb')}
            files = {'file': open(options['path_annotation_file'][0]+annotation_files[i], 'rb')}

            requests.post(url='http://127.0.0.1:8888'+reverse(viewname='doc_uploader', args=[project_id]), headers=headers, data=data, files=files)





    def get_labels(self):
        labels_list = []
        hierarchy = '/sharedWindows/NER/data/hierarchy.json'
        with open(hierarchy) as data_file:
            labels = json.load(data_file)

        for pattern in '1', '2', '3':
            level = 1
            labels_list = self.find_keys(pattern, labels, level, labels_list)

        labels_list = list(dict.fromkeys(labels_list))
        return labels_list

    def find_keys(self, pattern, labels, level, labels_list, is_bottom=False):
        is_splitted = False
        for i in range(0, 22):
            if is_bottom:
                if not is_splitted:
                    pattern_split = pattern.split('-')
                    pattern = str.join('-', pattern_split[:-1])
                    index = pattern_split[-1]
                    level = level - 1
                    is_splitted = True
                if (level==3) and (int(index)==21):
                    pattern = str.join('-', pattern_split[:-2])
                    index = pattern_split[-2]
                    level = level - 1
                elif i <= int(index):
                    continue
                else:
                    is_bottom = False
            if pattern=='':
                return labels_list
            pattern2 = pattern + '-' + str(i)
            # print('pattern2', pattern2)
            result = [(key, value) for key, value in labels.items() if key.startswith(pattern2)]
            if len(result) == 1:
                # print(result[0][1])
                labels_list.append(result[0][1])
            elif level < 4:
                level += 1
                result = [(key, value) for key, value in labels.items() if key.startswith(pattern2+'-')]
                if (not result) and (pattern2 in labels.keys()):
                    # print(labels[pattern2])
                    labels_list.append(labels[pattern2])
                    continue
                return self.find_keys(pattern2, labels, level, labels_list)
            elif level >= 4:
                return self.find_keys(pattern,labels, level, labels_list, is_bottom=True)

        return labels_list

