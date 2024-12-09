# coding=utf-8
from functools import reduce
from typing import List

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from application.flow.i_step_node import NodeResult
from application.flow.step_node.image_generate_step_node.i_image_generate_node import IImageGenerateNode
from setting.models_provider.tools import get_model_instance_by_model_user_id


class BaseImageGenerateNode(IImageGenerateNode):
    def save_context(self, details, workflow_manage):
        self.context['answer'] = details.get('answer')
        self.context['question'] = details.get('question')
        self.answer_text = details.get('answer')

    def execute(self, model_id, prompt, negative_prompt, dialogue_number, dialogue_type, history_chat_record, chat_id,
                chat_record_id,
                **kwargs) -> NodeResult:

        tti_model = get_model_instance_by_model_user_id(model_id, self.flow_params_serializer.data.get('user_id'))
        history_message = self.get_history_message(history_chat_record, dialogue_number)
        self.context['history_message'] = history_message
        question = self.generate_prompt_question(prompt)
        self.context['question'] = question
        message_list = self.generate_message_list(question, history_message)
        self.context['message_list'] = message_list
        self.context['dialogue_type'] = dialogue_type
        print(message_list)
        print(negative_prompt)
        image_urls = tti_model.generate_image(question, negative_prompt)
        self.context['image_list'] = image_urls
        answer = '\n'.join([f"![Image]({path})" for path in image_urls])
        return NodeResult({'answer': answer, 'chat_model': tti_model, 'message_list': message_list,
                           'image': [{'file_id': path.split('/')[-1], 'file_url': path} for path in file_urls],
                           'history_message': history_message, 'question': question}, {})

    def generate_history_ai_message(self, chat_record):
        for val in chat_record.details.values():
            if self.node.id == val['node_id'] and 'image_list' in val:
                if val['dialogue_type'] == 'WORKFLOW':
                    return chat_record.get_ai_message()
                return AIMessage(content=val['answer'])
        return chat_record.get_ai_message()

    def get_history_message(self, history_chat_record, dialogue_number):
        start_index = len(history_chat_record) - dialogue_number
        history_message = reduce(lambda x, y: [*x, *y], [
            [self.generate_history_human_message(history_chat_record[index]),
             self.generate_history_ai_message(history_chat_record[index])]
            for index in
            range(start_index if start_index > 0 else 0, len(history_chat_record))], [])
        return history_message

    def generate_history_human_message(self, chat_record):

        for data in chat_record.details.values():
            if self.node.id == data['node_id'] and 'image_list' in data:
                image_list = data['image_list']
                if len(image_list) == 0 or data['dialogue_type'] == 'WORKFLOW':
                    return HumanMessage(content=chat_record.problem_text)
                return HumanMessage(content=data['question'])
        return HumanMessage(content=chat_record.problem_text)

    def generate_prompt_question(self, prompt):
        return self.workflow_manage.generate_prompt(prompt)

    def generate_message_list(self, question: str, history_message):
        return [
            *history_message,
            question
        ]

    @staticmethod
    def reset_message_list(message_list: List[BaseMessage], answer_text):
        result = [{'role': 'user' if isinstance(message, HumanMessage) else 'ai', 'content': message.content} for
                  message
                  in
                  message_list]
        result.append({'role': 'ai', 'content': answer_text})
        return result

    def get_details(self, index: int, **kwargs):
        return {
            'name': self.node.properties.get('stepName'),
            "index": index,
            'run_time': self.context.get('run_time'),
            'history_message': [{'content': message.content, 'role': message.type} for message in
                                (self.context.get('history_message') if self.context.get(
                                    'history_message') is not None else [])],
            'question': self.context.get('question'),
            'answer': self.context.get('answer'),
            'type': self.node.type,
            'message_tokens': self.context.get('message_tokens'),
            'answer_tokens': self.context.get('answer_tokens'),
            'status': self.status,
            'err_message': self.err_message,
            'image_list': self.context.get('image_list'),
            'dialogue_type': self.context.get('dialogue_type')
        }